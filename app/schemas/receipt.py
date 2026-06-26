# app/schemas/receipt.py

from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import ReceiptType


# ==========================================================
# ЧЕКИ
# ==========================================================


class ReceiptItem(BaseModel):
    name: str
    quantity: int = 1
    price: Decimal
    total: Decimal

class ReceiptCreate(BaseModel):
    payment_id: UUID
    items: list[ReceiptItem]
    receipt_type: str = "SALE"
    original_receipt_id: UUID | None = None
    customer_email: str | None = None
    customer_phone: str | None = None

class ReceiptResponse(BaseModel):
    """Ответ с информацией о чеке"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    payment_id: UUID
    receipt_number: str
    receipt_type: str
    fiscal_sign: str | None
    fiscal_document_number: int | None
    fiscal_document_date: datetime | None
    ofd_url: str | None
    qr_code: str | None
    customer_email: str | None
    customer_phone: str | None
    is_sent: bool
    created_at: datetime


class ReceiptSendRequest(BaseModel):
    """Запрос на отправку чека"""
    
    email: str | None = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Email")
    phone: str | None = Field(None, description="Телефон")
    send_sms: bool = Field(default=False, description="Отправить SMS")


class ReceiptSendResponse(BaseModel):
    """Ответ на отправку чека"""
    
    success: bool
    sent_to: list[str] = Field(default_factory=list, description="Куда отправлено")
    message: str | None = None


class ReceiptGenerateRequest(BaseModel):
    """Запрос на генерацию чека"""
    
    payment_id: UUID
    receipt_type: ReceiptType = Field(default=ReceiptType.SALE)
    customer_email: str | None = None
    customer_phone: str | None = None