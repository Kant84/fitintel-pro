from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PaymentExportRequest(BaseModel):
    """Запрос на экспорт платежей"""
    
    date_from: Optional[date] = Field(
        default=None,
        description="Дата начала периода (YYYY-MM-DD)",
    )
    date_to: Optional[date] = Field(
        default=None,
        description="Дата окончания периода (YYYY-MM-DD)",
    )
    client_id: Optional[str] = Field(
        default=None,
        description="ID клиента (фильтр по клиенту)",
    )
    payment_direction: Optional[str] = Field(
        default=None,
        description="Направление: INCOME, EXPENSE",
    )
    payment_category: Optional[str] = Field(
        default=None,
        description="Категория: SUBSCRIPTION, SALARY, INVENTORY, RENT, UTILITIES, OTHER",
    )
    status: Optional[str] = Field(
        default=None,
        description="Статус: PENDING, COMPLETED, CANCELLED, REFUNDED",
    )
    format: str = Field(
        default="xlsx",
        description="Формат: xlsx, csv, pdf",
    )
