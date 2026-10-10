"""Волна 5: магазин (склад) + покупки с баланса кошелька ЛК.

- схема склада самочинится при старте: таблица, колонки club_id/article/photo_url,
  DEFAULT для id (у старых таблиц его не было) и демо-товары при пустом складе;
- buy_with_balance: атомарно  остаток -> WalletService.withdraw -> списание -> BarSale;
- create_balance_topup: онлайн-пополнение (банк из BANK_CONFIG, иначе тест-режим).
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text as _t
from sqlalchemy.orm import Session

from app.models.warehouse import WarehouseProduct, BarSale
from app.services.wallet_service import WalletService

_DEMO = [
    ("Протеиновый коктейль", "PR-001", 350),
    ("Вода 0.5", "WA-001", 100),
    ("Батончик энергетический", "BT-001", 150),
    ("Изотоник", "IS-001", 200),
]


def _apply_schema(exe) -> None:
    """exe: вызываемый execute (Session.execute или Connection.execute)."""
    tabs = {r[0] for r in exe(_t(
        "SELECT table_name FROM information_schema.tables WHERE table_name='warehouse_products'"))}
    if "warehouse_products" not in tabs:
        exe(_t(
            "CREATE TABLE warehouse_products ("
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "club_id INTEGER NOT NULL DEFAULT 1,"
            "category_id UUID, name VARCHAR(200) NOT NULL, description TEXT,"
            "unit VARCHAR(20) DEFAULT 'шт', cost_price NUMERIC(10,2) DEFAULT 0,"
            "sale_price NUMERIC(10,2) NOT NULL DEFAULT 0,"
            "quantity NUMERIC(10,3) DEFAULT 0, min_quantity NUMERIC(10,3) DEFAULT 10,"
            "barcode VARCHAR(50), supplier VARCHAR(200),"
            "is_active BOOLEAN DEFAULT TRUE, photo_url VARCHAR(500),"
            "article VARCHAR(50),"
            "created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now())"))
    else:
        # у старых таблиц id был WITHOUT DEFAULT — чиним
        exe(_t("ALTER TABLE warehouse_products ALTER COLUMN id SET DEFAULT gen_random_uuid()"))
    cols = {r[0] for r in exe(_t(
        "SELECT column_name FROM information_schema.columns WHERE table_name='warehouse_products'"))}
    if "club_id" not in cols:
        exe(_t("ALTER TABLE warehouse_products ADD COLUMN club_id INTEGER NOT NULL DEFAULT 1"))
        exe(_t("UPDATE warehouse_products SET club_id = 1 WHERE club_id IS NULL"))
    if "photo_url" not in cols:
        exe(_t("ALTER TABLE warehouse_products ADD COLUMN photo_url VARCHAR(500)"))
    if "article" not in cols:
        exe(_t("ALTER TABLE warehouse_products ADD COLUMN article VARCHAR(50)"))


def _seed_demo(exe) -> None:
    n = exe(_t("SELECT count(*) FROM warehouse_products")).scalar()
    if n:
        return
    for name, art, price in _DEMO:
        exe(_t(
            "INSERT INTO warehouse_products (club_id,name,article,sale_price,quantity,unit,is_active)"
            " VALUES (1,:n,:a,:p,20,'шт',TRUE)"), {"n": name, "a": art, "p": price})


def _ensure_shop_schema(db: Session) -> None:
    try:
        if db.bind.dialect.name != "postgresql":
            return
        _apply_schema(db.execute)
        _seed_demo(db.execute)
        db.commit()
    except Exception:
        db.rollback()


def _ensure_shop_schema_startup() -> None:
    from app.db.session import engine as _e
    try:
        with _e.begin() as c:
            _apply_schema(c.execute)
            _seed_demo(c.execute)
        print("W5 shop schema OK")
    except Exception as _e2:
        print("W5 shop schema:", str(_e2)[:120])


_ensure_shop_schema_startup()  # W5: auto-repair + demo goods on start


def buy_with_balance(db: Session, client_id, product_id, quantity: int = 1) -> dict:
    """Купить товар со списанием с баланса кошелька. HTTPException с понятным текстом."""
    if quantity < 1:
        raise HTTPException(400, "Количество должно быть ≥ 1")
    _ensure_shop_schema(db)
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
    except HTTPException:
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
    """Создать онлайн-платёж для пополнения кошелька (банк из BANK_CONFIG, иначе тест-режим)."""
    import uuid as _uuid
    from datetime import datetime as _dt, timezone as _tz

    if amount < 50 or amount > 50000:
        raise HTTPException(400, "Сумма пополнения: от 50 до 50 000 ₽")

    bank_res = None
    try:
        from app.api.v1.bank_online import create_bank_payment
        bank_res = create_bank_payment(db, client_id, amount, description)
    except HTTPException:
