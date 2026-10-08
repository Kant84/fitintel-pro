"""Волна 5: покупка товара с баланса кошелька (для десктопа/интеграций)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.services.shop_service import buy_with_balance

router = APIRouter(prefix="/shop", tags=["shop"])


class BuyIn(BaseModel):
    client_id: str
    product_id: str
    quantity: int = 1


@router.post("/buy-balance")
def buy(body: BuyIn, db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    """Оплата товара с баланса ЛК. Десктоп: продажа клиенту со списанием баланса."""
    return buy_with_balance(db, body.client_id, body.product_id, body.quantity)