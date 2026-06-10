# app/schemas/sale.py
from typing import List, Optional

from uuid import UUID
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field, ConfigDict


# ==========================================================
# ПРОДАЖА АБОНЕМЕНТА
# ==========================================================

class SaleSubscriptionRequest(BaseModel):
    """Продажа абонемента"""
    
    client_id: UUID = Field(description="ID клиента")
    tariff_id: UUID = Field(description="ID тарифа")
    payment_method: str = Field(description="Способ оплаты")
    start_date: date | None = Field(None, description="Дата начала (по умолчанию сегодня)")
    auto_renew: bool = Field(default=False, description="Автопродление")
    notes: str | None = Field(None, max_length=500)


class SaleSubscriptionResponse(BaseModel):
    """Ответ на продажу абонемента"""
    
    success: bool
    subscription_id: UUID
    payment_id: UUID
    receipt_id: UUID
    amount: Decimal
    message: str | None = None


# ==========================================================
# ПРОДАЖА УСЛУГИ
# ==========================================================

class SaleServiceRequest(BaseModel):
    """Продажа услуги"""
    
    client_id: UUID
    service_id: UUID
    quantity: int = Field(default=1, ge=1, le=100)
    payment_method: str
    notes: str | None = None


class SaleServiceResponse(BaseModel):
    """Ответ на продажу услуги"""
    
    success: bool
    sale_id: UUID
    payment_id: UUID
    receipt_id: UUID
    amount: Decimal
    message: str | None = None


# ==========================================================
# ПРОДАЖА РАЗОВОГО ПОСЕЩЕНИЯ
# ==========================================================

class SaleVisitRequest(BaseModel):
    """Продажа разового посещения"""
    
    client_id: UUID
    zone: str | None = Field(None, description="Зона клуба")
    payment_method: str
    notes: str | None = None


class SaleVisitResponse(BaseModel):
    """Ответ на продажу посещения"""
    
    success: bool
    visit_id: UUID
    payment_id: UUID
    receipt_id: UUID
    amount: Decimal
    message: str | None = None
# ============================================================
# SALE PACKAGE (комплексная продажа)
# ============================================================

class SalePackageRequest(BaseModel):
    """Запрос на комплексную продажу (пакет услуг)"""
    client_id: str
    items: list[str]
    discount_percent: Optional[int] = Field(0, ge=0, le=100)
    payment_method: str
    model_config = ConfigDict(str_strip_whitespace=True)


class SalePackageResponse(BaseModel):
    """Ответ на комплексную продажу"""
    success: bool
    sale_id: Optional[str] = None
    total_amount: float
    discount_amount: float
    final_amount: float
    items_sold: int
    receipt_number: Optional[str] = None
    model_config = ConfigDict(str_strip_whitespace=True)

