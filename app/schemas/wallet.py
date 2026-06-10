# app/schemas/wallet.py

from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import TransactionType


# ==========================================================
# КОШЕЛЁК
# ==========================================================

class WalletResponse(BaseModel):
    """Ответ с информацией о кошельке"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(description="ID кошелька")
    client_id: UUID = Field(description="ID клиента")
    balance: Decimal = Field(description="Текущий баланс", examples=[1500.50])
    currency: str = Field(description="Валюта", examples=["RUB"])
    frozen_balance: Decimal = Field(description="Замороженные средства", examples=[0.00])
    created_at: datetime
    updated_at: datetime


class WalletDepositRequest(BaseModel):
    """Запрос на пополнение баланса"""
    
    amount: Decimal = Field(gt=0, decimal_places=2, description="Сумма пополнения")
    payment_method: str = Field(description="Способ оплаты", examples=["CASH", "CARD"])
    notes: str | None = Field(None, max_length=500, description="Заметки")


class WalletDepositResponse(BaseModel):
    """Ответ на пополнение баланса"""
    
    success: bool
    wallet_id: UUID
    new_balance: Decimal
    transaction_id: UUID
    message: str | None = None


# ==========================================================
# ТРАНЗАКЦИИ
# ==========================================================

class WalletTransactionResponse(BaseModel):
    """Ответ с информацией о транзакции"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    wallet_id: UUID
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: str | None
    reference_type: str | None
    reference_id: str | None
    created_by_user_id: UUID | None
    created_at: datetime


class WalletTransactionListResponse(BaseModel):
    """Список транзакций"""
    
    items: list[WalletTransactionResponse]
    count: int
    total_deposited: Decimal | None = Field(None, description="Всего пополнено")
    total_withdrawn: Decimal | None = Field(None, description="Всего списано")


class WalletTransactionFilter(BaseModel):
    """Фильтр для транзакций"""
    
    transaction_type: TransactionType | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    reference_type: str | None = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)