"""Vending: оплата товаров автоматов с баланса клиента.

Каналы идентификации клиента:
  1) RFID-браслет (uid) — приложил к автомату, списание сразу (purchase);
  2) Код с экрана автомата — клиент вводит/сканирует его в миниаппе MAX
     (POST /vending/pay, авторизация Bearer), автомат выдаёт по опросу.
Автомат авторизуется заголовком X-Device-Token.
"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db, engine
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/vending", tags=["vending"])


def _ensure():
    with engine.begin() as c:
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS vending_devices (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                name varchar(128) NOT NULL,
                api_token varchar(64) NOT NULL UNIQUE,
                location varchar(255) DEFAULT '',
                is_active boolean NOT NULL DEFAULT true,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )"""))
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS vending_sales (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                device_id uuid NOT NULL REFERENCES vending_devices(id),
                client_id uuid NOT NULL,
                client_label varchar(255) DEFAULT '',
                product_name varchar(255) NOT NULL,
                price numeric(10,2) NOT NULL,
                status varchar(20) NOT NULL DEFAULT 'PENDING',
                error text,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )"""))
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS vending_sessions (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                device_id uuid NOT NULL REFERENCES vending_devices(id),
                code varchar(6) NOT NULL UNIQUE,
                status varchar(20) NOT NULL DEFAULT 'OPEN',
                client_id uuid,
                client_label varchar(255) DEFAULT '',
                product_name varchar(255) NOT NULL,
                price numeric(10,2) NOT NULL,
                sale_id uuid,
                expires_at timestamptz,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )"""))


def _device(token: str | None):
    if not token:
        raise HTTPException(401, "X-Device-Token обязателен")
    _ensure()
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT id, name, is_active FROM vending_devices WHERE api_token=:t"),
            {"t": token}).first()
    if not row or not row[2]:
        raise HTTPException(403, "Устройство не найдено или отключено")
    return {"id": str(row[0]), "name": row[1]}


def _price(body: dict):
    product = str(body.get("product_name") or "Товар").strip()[:250]
    try:
        price = Decimal(str(body.get("price"))).quantize(Decimal("0.01"))
    except Exception:
        price = Decimal("0")
    if price <= 0:
        raise HTTPException(400, "price должен быть положительным числом")
    return product, price


def _client_by_uid(db: Session, uid: str):
    try:
        row = db.execute(text(
            "SELECT client_id FROM credentials WHERE uid=:u ORDER BY created_at LIMIT 1"),
            {"u": uid}).first()
        return str(row[0]) if row else None
    except Exception:
        return None


def _do_sale(db: Session, device_id: str, device_name: str, client_id: str,
             label: str, product: str, price: Decimal):
    """Списание с баланса + запись продажи. Исключение HTTPException — отказ."""
    sale_id = str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO vending_sales (id, device_id, client_id, client_label, product_name, price, status)
            VALUES (:i, :d, :cl, :lb, :p, :pr, 'PENDING')
        """), {"i": sale_id, "d": device_id, "cl": client_id, "lb": label,
               "p": product, "pr": price})
    wallet, _tx = WalletService(db).withdraw(
        client_id=client_id, amount=price,
        description=f"Вендинг ({device_name}): {product}",
        reference_type="vending_sale", reference_id=sale_id)
    with engine.begin() as c:
        c.execute(text("UPDATE vending_sales SET status='PAID', updated_at=now() WHERE id=:i"),
                  {"i": sale_id})
    return sale_id, wallet


@router.post("/purchase")
def purchase(body: dict, x_device_token: str | None = Header(None),
             db: Session = Depends(get_db)):
    """Канал 1 (RFID): приложил браслет — списание сразу."""
    dev = _device(x_device_token)
    product, price = _price(body)

    client_id = body.get("client_id")
    uid = str(body.get("uid") or "").strip()
    if not client_id and uid:
        client_id = _client_by_uid(db, uid)
    if not client_id:
        raise HTTPException(404, "Клиент не найден (приложите браслет или код)")

    label = str(body.get("client_label") or "")
    try:
        sale_id, wallet = _do_sale(db, dev["id"], dev["name"], str(client_id),
                                   label, product, price)
    except HTTPException as e:
        sale_id = None
        with engine.begin() as c:
            row = c.execute(text(
                "SELECT id FROM vending_sales WHERE device_id=:d ORDER BY created_at DESC LIMIT 1"),
                {"d": dev["id"]}).first()
            if row:
                sale_id = str(row[0])
                c.execute(text("UPDATE vending_sales SET status='DECLINED', error=:e, updated_at=now() WHERE id=:i"),
                          {"e": str(e.detail), "i": sale_id})
        return {"allow": False, "sale_id": sale_id, "reason": e.detail}
    return {"allow": True, "sale_id": sale_id, "price": str(price),
            "balance_after": str(wallet.balance), "client_id": client_id}


@router.post("/session")
def create_session(body: dict, x_device_token: str | None = Header(None)):
    """Автомат создаёт сессию оплаты: на экране — 6-значный код (и QR с ним)."""
    dev = _device(x_device_token)
    product, price = _price(body)
    _ensure()
    with engine.begin() as c:
        for _ in range(20):
            code = f"{random.randint(0, 999999):06d}"
            clash = c.execute(text("SELECT 1 FROM vending_sessions WHERE code=:c"),
                              {"c": code}).first()
            if not clash:
                break
        else:
            raise HTTPException(500, "Не удалось создать код, повторите")
        sid = str(uuid.uuid4())
        c.execute(text("""
            INSERT INTO vending_sessions (id, device_id, code, status, product_name, price, expires_at)
            VALUES (:i, :d, :c, 'OPEN', :p, :pr, now() + interval '10 minutes')
        """), {"i": sid, "d": dev["id"], "c": code, "p": product, "pr": price})
    return {"session_id": sid, "code": code, "product": product,
            "price": str(price), "qr_text": code}


@router.get("/session/{code}")
def poll_session(code: str, x_device_token: str | None = Header(None)):
    """Автомат опрашивает статус сессии; при PAID выдаёт товар."""
    dev = _device(x_device_token)
    with engine.connect() as c:
        row = c.execute(text("""
            SELECT status, product_name, price, client_label, sale_id::text, expires_at
            FROM vending_sessions WHERE code=:c AND device_id=:d
        """), {"c": str(code), "d": dev["id"]}).first()
    if not row:
        raise HTTPException(404, "Сессия не найдена")
    return {"status": row[0], "product": row[1], "price": str(row[2]),
            "client_label": row[3] or "", "sale_id": row[4],
            "expires_at": str(row[5]) if row[5] else None}


@router.post("/pay")
def pay(body: dict, current=Depends(__import__("app.api.dependencies", fromlist=["get_current_user"]).get_current_user),
        db: Session = Depends(get_db)):
    """Канал 2 (миниапп MAX): клиент вводит код с экрана автомата."""
    code = str(body.get("code") or "").strip()
    if not code:
        raise HTTPException(400, "code обязателен")
    _ensure()
    with engine.connect() as c:
        srow = c.execute(text("""
            SELECT id::text, status, product_name, price, expires_at, device_id::text
            FROM vending_sessions WHERE code=:c
        """), {"c": code}).first()
    if not srow:
        raise HTTPException(404, "Сессия не найдена")
    if srow[1] != "OPEN":
        raise HTTPException(409, "Сессия уже оплачена или закрыта")
    if srow[4] and datetime.now(timezone.utc) > srow[4]:
        raise HTTPException(410, "Сессия истекла — начните на автомате заново")

    uid = str(current.id)
    crow = db.execute(text("SELECT id FROM clients WHERE user_id=:u LIMIT 1"),
                      {"u": uid}).first()
    if not crow:
        raise HTTPException(404, "Карточка клиента не найдена")
    client_id = str(crow[0])
    uname = db.execute(text("SELECT full_name FROM users WHERE id=:u"), {"u": uid}).first()
    label = (uname[0] if uname and uname[0] else "Клиент")

    with engine.connect() as c:
        dname = c.execute(text("SELECT name FROM vending_devices WHERE id=:d"),
                          {"d": srow[5]}).first()
    device_name = dname[0] if dname else "вендинг"

    try:
        sale_id, wallet = _do_sale(db, srow[5], device_name, client_id,
                                   label, srow[2], Decimal(str(srow[3])))
    except HTTPException as e:
        return {"ok": False, "reason": e.detail}
    with engine.begin() as c:
        c.execute(text("""
            UPDATE vending_sessions SET status='PAID', client_id=:cl, client_label=:lb,
                sale_id=:s, updated_at=now() WHERE id=:i
        """), {"cl": client_id, "lb": label, "s": sale_id, "i": srow[0]})
    return {"ok": True, "product": srow[2], "price": str(srow[3]),
            "balance_after": str(wallet.balance), "sale_id": sale_id}


@router.post("/confirm")
def confirm(body: dict, x_device_token: str | None = Header(None),
            db: Session = Depends(get_db)):
    """Автомат подтверждает выдачу; при сбое — возврат на баланс."""
    _device(x_device_token)
    sale_id = str(body.get("sale_id") or "")
    status = str(body.get("status") or "").lower()
    if status not in ("dispensed", "failed"):
        raise HTTPException(400, "status: dispensed|failed")
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT client_id, price, product_name, status FROM vending_sales WHERE id=:i"),
            {"i": sale_id}).first()
    if not row:
        raise HTTPException(404, "Продажа не найдена")
    client_id, price, product, cur = str(row[0]), Decimal(str(row[1])), row[2], row[3]
    if cur != "PAID":
        return {"ok": True, "sale_id": sale_id, "status": cur, "note": "уже обработано"}
    if status == "failed":
        WalletService(db).deposit(
            client_id=client_id, amount=price, payment_method="REFUND",
            notes=f"Возврат вендинг: {product}", reference_type="vending_sale",
            reference_id=sale_id)
        new_status = "REFUNDED"
    else:
        new_status = "CONFIRMED"
    with engine.begin() as c:
        c.execute(text("UPDATE vending_sales SET status=:s, updated_at=now() WHERE id=:i"),
                  {"s": new_status, "i": sale_id})
    if new_status == "CONFIRMED":
        try:
            from app.services.client_notify_service import ClientNotifyService
            ClientNotifyService(db).send(
                client_id, "vending",
                f"Покупка «{product}» на сумму {price} ₽. Спасибо!")
        except Exception:
            pass
    return {"ok": True, "sale_id": sale_id, "status": new_status}


@router.get("/sales")
def sales(limit: int = 50, x_device_token: str | None = Header(None)):
    dev = _device(x_device_token)
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT id::text, client_label, product_name, price, status, created_at
            FROM vending_sales WHERE device_id=:d ORDER BY created_at DESC LIMIT :l
        """), {"d": dev["id"], "l": min(limit, 500)}).all()
    return {"items": [dict(r._mapping) for r in rows]}
