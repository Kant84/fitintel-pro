# app/schemas/cash_desk.py

from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import CashOperationType, PaymentMethod, CashDeskStatus


# ==========================================================
# КАССОВЫЕ СМЕНЫ
# ==========================================================

class CashDeskOpenRequest(BaseModel):
    """Запрос на открытие смены"""
    
    opening_balance: Decimal = Field(default=0.00, ge=0, description="Начальный остаток")
    notes: str | None = Field(None, max_length=500, description="Заметки")


class CashDeskCloseRequest(BaseModel):
    """Запрос на закрытие смены"""
    
    actual_cash: Decimal = Field(ge=0, description="Фактическая наличность")
    notes: str | None = Field(None, max_length=500, description="Заметки")


class CashDeskSessionResponse(BaseModel):
    """Ответ с информацией о смене"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    session_number: int
    cashier_user_id: UUID
    cashier_name: str | None = None
    opened_at: datetime
    closed_at: datetime | None
    opening_balance: Decimal
    closing_balance: Decimal | None
    cash_income: Decimal
    cash_outcome: Decimal
    card_income: Decimal
    expected_cash: Decimal | None
    actual_cash: Decimal | None
    discrepancy: Decimal | None
    status: str
    notes: str | None
    created_at: datetime


class CashDeskSessionListResponse(BaseModel):
    """Список смен"""
    
    items: list[CashDeskSessionResponse]
    count: int
    total_cash_income: Decimal = Field(description="Всего наличных поступлений")
    total_card_income: Decimal = Field(description="Всего безналичных поступлений")


class CashDeskCurrentResponse(BaseModel):
    """Текущая смена"""
    
    has_open_session: bool
    session: CashDeskSessionResponse | None = None


# ==========================================================
# КАССОВЫЕ ОПЕРАЦИИ
# ==========================================================

class CashOperationCreateRequest(BaseModel):
    """Запрос на создание кассовой операции"""
    
    operation_type: CashOperationType
    amount: Decimal = Field(gt=0, decimal_places=2, description="Сумма")
    payment_method: PaymentMethod
    reference_type: str | None = None
    reference_id: str | None = None
    description: str | None = Field(None, max_length=500)


class CashOperationResponse(BaseModel):
    """Ответ с информацией о кассовой операции"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    session_id: UUID
    operation_type: str
    amount: Decimal
    payment_method: str
    reference_type: str | None
    reference_id: str | None
    description: str | None
    created_by_user_id: UUID | None
    created_at: datetime


class CashOperationListResponse(BaseModel):
    """Список кассовых операций"""
    
    items: list[CashOperationResponse]
    count: int
    total_income: Decimal = Field(description="Всего поступлений")
    total_outcome: Decimal = Field(description="Всего выплат")