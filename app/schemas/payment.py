# app/schemas/payment.py

from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import PaymentMethod, PaymentStatus, PaymentSystem


# ==========================================================
# ОСНОВНЫЕ СХЕМЫ
# ==========================================================

class PaymentBase(BaseModel):
    """Базовые поля платежа"""
    
    client_id: UUID | None = Field(default=None, description="ID клиента (None для внутренних платежей)")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Сумма")
    payment_method: PaymentMethod = Field(description="Способ оплаты")
    payment_system: PaymentSystem | None = Field(None, description="Платёжная система")
    notes: str | None = Field(None, max_length=500, description="Заметки")
    
    # Направление платежа
    payment_direction: str = Field(
        default="INCOME",
        description="Направление: INCOME (приход), EXPENSE (расход)",
    )
    
    # Категория платежа
    payment_category: str = Field(
        default="SUBSCRIPTION",
        description="Категория: SUBSCRIPTION, INVENTORY, SALARY, RENT, UTILITIES, OTHER",
    )


class PaymentCreateRequest(PaymentBase):
    """Создание платежа"""
    
    return_url: str | None = Field(None, description="URL для возврата после оплаты")
    webhook_url: str | None = Field(None, description="URL для уведомлений")
    
    # Для СБП
    sbp_qr_code: bool = Field(default=False, description="Сгенерировать QR-код СБП")
    sbp_bank_id: str | None = Field(None, description="ID банка для СБП")
    
class PaymentResponse(PaymentBase):
    """Ответ с информацией о платеже (полные данные как в чеке)"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: str
    external_payment_id: str | None
    paid_at: datetime | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    
    # Данные клиента (как в чеке)
    client_first_name: str | None = Field(default=None, description="Имя клиента")
    client_last_name: str | None = Field(default=None, description="Фамилия клиента")
    client_middle_name: str | None = Field(default=None, description="Отчество клиента")
    client_full_name: str | None = Field(default=None, description="Полное ФИО клиента")
    client_phone: str | None = Field(default=None, description="Телефон клиента")
    client_email: str | None = Field(default=None, description="Email клиента")
    
    # Вид платежа
    payment_type: str | None = Field(default=None, description="Вид платежа: Наличные/Безналичные")
    
    # Банк/платёжная система
    bank_name: str | None = Field(default=None, description="Название банка или платёжной системы")
    
    # Данные чека
    receipt_number: str | None = Field(default=None, description="Номер чека")
    
    # За что оплачено
    purpose: str | None = Field(default=None, description="Назначение платежа (абонемент/услуга)")
    subscription_name: str | None = Field(default=None, description="Название абонемента")


class PaymentListResponse(BaseModel):
    """Список платежей"""
    
    items: list[PaymentResponse]
    count: int
    total_amount: Decimal = Field(description="Общая сумма")


class PaymentCompleteRequest(BaseModel):
    """Подтверждение платежа"""
    
    external_payment_id: str | None = Field(None, description="ID во внешней системе")
    transaction_data: dict | None = Field(None, description="Данные транзакции")


class PaymentRefundRequest(BaseModel):
    """Запрос на возврат"""
    
    amount: Decimal | None = Field(None, description="Сумма возврата (если не указана — полный)")
    reason: str = Field(min_length=1, max_length=255, description="Причина возврата")
    refund_to_balance: bool = Field(default=False, description="Вернуть на баланс кошелька")


class PaymentRefundResponse(BaseModel):
    """Ответ на возврат"""
    
    success: bool
    refund_id: UUID
    refunded_amount: Decimal
    message: str | None = None


# ==========================================================
# ДЛЯ ОНЛАЙН-ПЛАТЕЖЕЙ
# ==========================================================

class PaymentOnlineResponse(BaseModel):
    """Ответ для онлайн-платежа"""
    
    payment_id: UUID
    payment_url: str | None = Field(None, description="Ссылка на оплату")
    requires_redirect: bool = Field(default=False, description="Требуется редирект")
    transaction_id: str | None = Field(None, description="ID транзакции в платёжной системе")
    
    # Для СБП
    sbp_qr_code: str | None = Field(None, description="QR-код для оплаты по СБП (base64)")
    sbp_qr_code_url: str | None = Field(None, description="URL QR-кода СБП")
    sbp_deeplink: str | None = Field(None, description="Глубокая ссылка для приложения банка")


class PaymentWebhookRequest(BaseModel):
    """Вебхук от платёжной системы"""
    
    payment_id: str = Field(description="ID платежа")
    status: str = Field(description="Статус платежа")
    transaction_id: str | None = None
    amount: Decimal | None = None
    raw_data: dict = Field(description="Сырые данные от платёжной системы")