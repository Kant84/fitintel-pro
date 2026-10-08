"""Волна 5: покупки в магазине оплатой с баланса кошелька (ЛК клиента).

Цепочка (атомарно в одной сессии):
  остаток товара >= кол-ва  ->  WalletService.withdraw (проверка/списание, транзакция)
  ->  списание остатка  ->  BarSale (payment_method=BALANCE).
Используется ботом MAX напрямую (in-process) и endpoint'ом /shop/buy-balance.
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.warehouse import _ensure_warehouse
from app.models.warehouse import WarehouseProduct, BarSale
from app.services.wallet_service import WalletService


def buy_with_balance(db: Session, client_id, product_id, quantity: int = 1) -> dict:
    """Купить товар со списанием с баланса кошелька. HTTPException с понятным текстом."""
    if quantity < 1:
        raise HTTPException(400, "Количество должно быть ≥ 1")
    _ensure_warehouse(db)
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