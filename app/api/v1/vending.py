"""Vending: оплата товаров автоматов с баланса клиента.

Автомат авторизуется заголовком X-Device-Token (устройство создаётся
администратором SQL'ем/скриптом — см. tools/mock_vending.py).
Идентификация клиента: uid RFID-браслета или client_id (эмуляция/тесты).
"""
import uuid
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


def _device(token: str | None):
    if not token:
        raise HTTPException(401, "X-Device-Token обязателен")
    _ensure()
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT id, name, is_active FROM vending_devices WHERE api_token=:t"), {"t": token}).first()
    if not row or not row[2]:
        raise HTTPException(403, "Устройство не найдено или отключено")
    return {"id": str(row[0]), "name": row[1]}


def _client_by_uid(db: Session, uid: str):
    try:
        row = db.execute(text(
            "SELECT client_id FROM credentials WHERE uid=:u ORDER BY created_at LIMIT 1"),
            {"u": uid}).first()
        return str(row[0]) if row else None
    except Exception:
        return None


@router.post("/purchase")
def purchase(body: dict, x_device_token: str | None = Header(None),
             db: Session = Depends(get_db)):
    """Автомат запрашивает разрешение на продажу и списывает сумму с баланса."""
    dev = _device(x_device_token)
    product = str(body.get("product_name") or "Товар").strip()[:250]
    try:
        price = Decimal(str(body.get("price"))).quantize(Decimal("0.01"))
    except Exception:
        price = Decimal("0")
    if price <= 0:
        raise HTTPException(400, "price должен быть положительным числом")

    client_id = body.get("client_id")
    uid = str(body.get("uid") or "").strip()
    if not client_id and uid:
        client_id = _client_by_uid(db, uid)
    if not client_id:
        raise HTTPException(404, "Клиент не найден (приложите браслет или код)")

    label = str(body.get("client_label") or "")
    sale_id = str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO vending_sales (id, device_id, client_id, client_label, product_name, price, status)
            VALUES (:i, :d, :cl, :lb, :p, :pr, 'PENDING')
        """), {"i": sale_id, "d": dev["id"], "cl": client_id, "lb": label,
               "p": product, "pr": price})

    try:
        wallet, tx = WalletService(db).withdraw(
            client_id=client_id, amount=price,
            description=f"Вендинг ({dev['name']}): {product}",
            reference_type="vending_sale", reference_id=sale_id)
    except HTTPException as e:
        with engine.begin() as c:
            c.execute(text("UPDATE vending_sales SET status='DECLINED', error=:e, updated_at=now() WHERE id=:i"),
                      {"e": str(e.detail), "i": sale_id})
        return {"allow": False, "sale_id": sale_id, "reason": e.detail}

    with engine.begin() as c:
        c.execute(text("UPDATE vending_sales SET status='PAID', updated_at=now() WHERE id=:i"), {"i": sale_id})
    return {"allow": True, "sale_id": sale_id, "price": str(price),
            "balance_after": str(wallet.balance), "client_id": client_id}


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
