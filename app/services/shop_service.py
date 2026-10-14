"""Волна 5: магазин (склад) + покупки с баланса кошелька ЛК.

- схема склада самочинится при старте (таблица, колонки club_id/article/photo_url, DEFAULT id);
- наполнение — только из десктопа («Магазин»); здесь демо-данных НЕТ;
- buy_with_balance: атомарно  остаток -> WalletService.withdraw -> списание -> BarSale;
- create_balance_topup: онлайн-пополнение (банк из BANK_CONFIG, иначе тест-режим).
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text as _t
from sqlalchemy.orm import Session

from app.models.warehouse import WarehouseProduct, BarSale
from app.services.wallet_service import WalletService


def _apply_schema(exe) -> None:
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

    # фиксация продаж магазина (модель BarSale)
    exe(_t("CREATE TABLE IF NOT EXISTS bar_sales ("
           "id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
           "club_id INTEGER NOT NULL, client_id UUID, item_type VARCHAR(20),"
           "product_id UUID, recipe_id UUID, item_name VARCHAR(200),"
           "quantity NUMERIC(10,3) NOT NULL DEFAULT 1,"
           "unit_price NUMERIC(10,2) NOT NULL, total_price NUMERIC(10,2) NOT NULL,"
           "payment_method VARCHAR(20), status VARCHAR(20) DEFAULT 'completed',"
           "created_by UUID, created_at TIMESTAMP DEFAULT now())"))

    # движения склада (модель StockMovement)
    exe(_t("CREATE TABLE IF NOT EXISTS stock_movements ("
           "id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
           "club_id INTEGER NOT NULL, product_id UUID NOT NULL,"
           "type VARCHAR(20), quantity NUMERIC(10,3) NOT NULL,"
           "unit_cost NUMERIC(10,2), total_cost NUMERIC(10,2),"
           "reason VARCHAR(200), document_ref VARCHAR(100),"
           "created_by UUID, created_at TIMESTAMP DEFAULT now())"))


def _ensure_shop_schema_startup() -> None:
    from app.db.session import engine as _e
    try:
        with _e.begin() as c:
            _apply_schema(c.execute)
        print("W5 shop schema OK")
    except Exception as _e2:
        print("W5 shop schema:", str(_e2)[:120])


_ensure_shop_schema_startup()


def _ensure_shop_schema(db: Session) -> None:
    try:
        if db.bind.dialect.name != "postgresql":
            return
        _apply_schema(db.execute)
        db.commit()
    except Exception:
        db.rollback()


def buy_with_balance(db: Session, client_id, product_id, quantity: int = 1, method: str = "balance", bonus_percent: float = 0) -> dict:
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

    bonuses_used = Decimal("0")
    cash_part = total
    pay_method = "BALANCE"
    bonus_left = None
    from app.api.v1.club_params import get_param
    pct_cap = Decimal(str(float(get_param("BONUS_PAY_MAX_PERCENT", "30") or 30)))
    rate = Decimal(str(float(get_param("BONUS_TO_RUB_RATE", "1") or 1)))
    min_cash = Decimal(str(float(get_param("BONUS_MIN_CASH", "1") or 1)))
    if rate <= 0:
        rate = Decimal("1")
    bp = Decimal(str(bonus_percent or 0))
    if str(method).lower() == "bonuses" and bp <= 0:
        bp = pct_cap
    if bp > 0:
        bp = min(bp, pct_cap)
        g = db.execute(_t("SELECT current_xp FROM gamification_levels "
                          "WHERE replace(cast(client_id as varchar),'-','')=replace(cast(:c as varchar),'-','') LIMIT 1"),
                       {"c": str(client_id)}).first()
        avail = Decimal(str(g[0] if g and g[0] is not None else 0))
        bonus_rub = min(total * bp / 100, avail * rate)
        if total - bonus_rub < min_cash:
            bonus_rub = total - min_cash
        if bonus_rub < 0:
            bonus_rub = Decimal("0")
        bonus_rub = bonus_rub.quantize(Decimal("0.01"))
        deduct = (bonus_rub / rate).quantize(Decimal("0.01"))
        if deduct > 0:
            if avail < deduct:
                raise HTTPException(400, "Недостаточно бонусов: на счету %s" % avail)
            db.execute(_t("UPDATE gamification_levels SET current_xp=current_xp-:d, updated_at=now() "
                          "WHERE replace(cast(client_id as varchar),'-','')=replace(cast(:c as varchar),'-','')"),
                       {"d": deduct, "c": str(client_id)})
            db.commit()
        bonuses_used = deduct
        cash_part = total - bonus_rub
        pay_method = "BONUSES" if cash_part <= 0 else "MIXED"
        gl = db.execute(_t("SELECT current_xp FROM gamification_levels "
                           "WHERE replace(cast(client_id as varchar),'-','')=replace(cast(:c as varchar),'-','') LIMIT 1"),
                        {"c": str(client_id)}).scalar()
        bonus_left = float(gl or 0)

    wallet = None
    if cash_part > 0:
        ws = WalletService(db)
        try:
            wallet, tx = ws.withdraw(
                str(client_id), cash_part,
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
                   payment_method=pay_method))
    db.commit()
    # W6: бонусы за покупку (на денежную часть) + пуш
    bonus_awarded = 0.0
    try:
        if cash_part > 0:
            from app.api.v1.miniapp_config import award_bonus, _max_send
            bonus_awarded = float(award_bonus(db, str(client_id), "purchase", float(cash_part)) or 0)
        ph = db.execute(_t("SELECT phone FROM clients "
                           "WHERE replace(cast(id as varchar),'-','')=replace(cast(:c as varchar),'-','') LIMIT 1"),
                        {"c": str(client_id)}).first()
        if ph and ph[0]:
            msg = "\U0001f6cd \u041a\u0443\u043f\u043b\u0435\u043d\u043e: %s \u00d7%d \u2014 " % (p.name, quantity)
            if bonuses_used > 0 and cash_part > 0:
                msg += "\u0431\u043e\u043d\u0443\u0441\u044b %s + %s \u20bd \u0441 \u0431\u0430\u043b\u0430\u043d\u0441\u0430" % (bonuses_used, cash_part)
            elif bonuses_used > 0:
                msg += "\u043e\u043f\u043b\u0430\u0447\u0435\u043d\u043e \u0431\u043e\u043d\u0443\u0441\u0430\u043c\u0438: %s" % bonuses_used
            else:
                msg += "%s \u20bd \u0441 \u0431\u0430\u043b\u0430\u043d\u0441\u0430" % total
            if bonus_awarded > 0:
                msg += " | \U0001f381 +%d \u0431\u043e\u043d\u0443\u0441\u043e\u0432 \u0441 \u043f\u043e\u043a\u0443\u043f\u043a\u0438" % int(bonus_awarded)
            _max_send(str(ph[0]), msg)
    except Exception as _w6e:
        import traceback; traceback.print_exc()
    bal = float(wallet.balance) if wallet is not None else None
    return {"ok": True, "product": p.name, "quantity": quantity, "method": str(method).lower(),
            "total": float(total), "bonuses_used": float(bonuses_used), "cash_paid": float(cash_part),
            "bonuses_left": bonus_left, "balance": bal}


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
        raise
    except Exception:
        bank_res = None
    if bank_res:
        return {"payment_id": None, "payment_url": bank_res["payment_url"],
                "test_mode": False}

    yk_id = f"yk-{_uuid.uuid4().hex[:16]}"
    url = f"https://yookassa.ru/payments/{yk_id}?test=true"

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
                  f"VALUES ({', '.join(':' + k for k in data)})"), data)
    db.commit()
    return {"payment_id": data["id"], "payment_url": url, "test_mode": True}