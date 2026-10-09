"""Волна 5: покупки в магазине оплатой с баланса кошелька (ЛК клиента).

Цепочка (атомарно в одной сессии):
  остаток товара >= кол-ва  ->  WalletService.withdraw (проверка/списание, транзакция)
  ->  списание остатка  ->  BarSale (payment_method=BALANCE).
Используется ботом MAX напрямую (in-process) и endpoint'ом /shop/buy-balance.
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.warehouse import WarehouseProduct, BarSale
from app.services.wallet_service import WalletService


def _ensure_shop_tables(db: Session):
    """Мини-миграция склада локально в сервисе (не зависит от api/v1/warehouse.py):
    таблица warehouse_products + колонки photo_url/article (идемпотентно)."""
    from sqlalchemy import text as _t
    try:
        if db.bind.dialect.name == "postgresql":
            tabs = {r[0] for r in db.execute(_t(
                "SELECT table_name FROM information_schema.tables WHERE table_name='warehouse_products'"))}
            if "warehouse_products" not in tabs:
                db.execute(_t(
                    "CREATE TABLE warehouse_products (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
                    " club_id INTEGER NOT NULL DEFAULT 1, category_id UUID, name VARCHAR(200) NOT NULL,"
                    " description TEXT, unit VARCHAR(20) DEFAULT 'шт', cost_price NUMERIC(10,2) DEFAULT 0,"
                    " sale_price NUMERIC(10,2) NOT NULL DEFAULT 0, quantity NUMERIC(10,3) DEFAULT 0,"
                    " min_quantity NUMERIC(10,3) DEFAULT 10, barcode VARCHAR(50), supplier VARCHAR(200),"
                    " is_active BOOLEAN DEFAULT TRUE, photo_url VARCHAR(500), article VARCHAR(50),"
                    " created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now())"))
            cols = {r[0] for r in db.execute(_t(
                "SELECT column_name FROM information_schema.columns WHERE table_name='warehouse_products'"))}
            if "photo_url" not in cols:
                db.execute(_t("ALTER TABLE warehouse_products ADD COLUMN photo_url VARCHAR(500)"))
            if "article" not in cols:
                db.execute(_t("ALTER TABLE warehouse_products ADD COLUMN article VARCHAR(50)"))
            db.commit()
    except Exception:
        db.rollback()


def buy_with_balance(db: Session, client_id, product_id, quantity: int = 1) -> dict:
    """Купить товар со списанием с баланса кошелька. HTTPException с понятным текстом."""
    if quantity < 1:
        raise HTTPException(400, "Количество должно быть ≥ 1")
    _ensure_shop_tables(db)
    p = (db.query(WarehouseProduct)
         .filter(WarehouseProduct.id == str(product_id),
                 WarehouseProduct.is_active.is_(True))
         .first())
    if not p:
        raise HTTPException(404, "Товар не найден")
    qty = Decimal(str(quantity))
    if (p.quantity or 0) < qty:
        raise HTTPException(400, f"Недостаточно остатка: {p.quantity} шт")

    total = Decimal(str(p.sale_price or 0)) * qty

    ws = WalletService(db)
    try:
        wallet, tx = ws.withdraw(
            str(client_id), total,
            description=f"Магазин: {p.name} ×{quantity}",
            reference_type="shop_product", reference_id=str(p.id))
    except HTTPException as e:
        # недостаточно средств / нет кошелька — текст уже понятный
        raise
    except Exception as e:
        raise HTTPException(400, f"Оплата с баланса не прошла: {str(e)[:120]}")

    p.quantity = (p.quantity or 0) - qty
    db.add(BarSale(club_id=p.club_id, client_id=str(client_id), item_type="product",
                   product_id=p.id, item_name=p.name, quantity=qty,
                   unit_price=p.sale_price, total_price=total,
                   payment_method="BALANCE"))
    db.commit()
    return {"ok": True, "product": p.name, "quantity": quantity,
            "total": float(total), "balance": float(wallet.balance)}


def create_balance_topup(db: Session, client_id, amount: float, description: str = "Пополнение баланса ЛК") -> dict:
    """Создать онлайн-платёж для пополнения кошелька (ЮKassa).
    Webhook /yookassa/webhook (payment.succeeded) зачисляет сумму на кошелёк сам.
    Без ключей YOOKASSA_* — тестовый режим (ссылка-заглушка)."""
    import uuid as _uuid
    from datetime import datetime as _dt, timezone as _tz
    from sqlalchemy import text as _t

    if amount < 50 or amount > 50000:
        raise HTTPException(400, "Сумма пополнения: от 50 до 50 000 ₽")

    # 1) банковский эквайринг (Сбер/Тинькофф из server_settings.BANK_CONFIG)
    bank_res = None
    try:
        from app.api.v1.bank_online import create_bank_payment
        bank_res = create_bank_payment(db, client_id, amount, description)
    except HTTPException:
        raise
    except Exception:
        bank_res = None
    if bank_res:
        # платёж уже записан create_bank_payment
        return {"payment_id": None, "payment_url": bank_res["payment_url"],
                "test_mode": False}
    # 2) тестовый режим (ссылка-заглушка)
    yk_id = f"yk-{_uuid.uuid4().hex[:16]}"
    url = f"https://yookassa.ru/payments/{yk_id}?test=true"
    test = True

    now = _dt.now(_tz.utc)
    cols = {r[0] for r in db.execute(_t(
        "SELECT column_name FROM information_schema.columns WHERE table_name='payments'"))}
    data = {"id": str(_uuid.uuid4()), "client_id": str(client_id), "amount": amount,
            "currency": "RUB", "payment_method": "bank_card", "status": "pending",
            "external_payment_id": yk_id, "payment_system": "yookassa",
            "notes": description, "payment_direction": "incoming",
            "payment_category": "service",
            "created_at": now, "updated_at": now}
    data = {k: v for k, v in data.items() if k in cols}
    db.execute(_t(f"INSERT INTO payments ({', '.join(data)}) "
                  f"VALUES ({', '.join(':'+k for k in data)})"), data)
    db.commit()
    return {"payment_id": data["id"], "payment_url": url, "test_mode": test}


def _ensure_shop_club_id() -> None:
    from app.db.session import engine as _e
    from sqlalchemy import text as _t
    with _e.begin() as _c:
        _c.execute(_t("ALTER TABLE warehouse_products ADD COLUMN IF NOT EXISTS club_id INTEGER DEFAULT 1"))
        _c.execute(_t("UPDATE warehouse_products SET club_id = 1 WHERE club_id IS NULL"))

_ensure_shop_club_id()  # W5 ensure: auto-repair schema on start
