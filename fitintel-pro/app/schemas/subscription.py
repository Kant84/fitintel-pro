# app/schemas/subscription.py

# импорт UUID
from uuid import UUID

# импорт date и datetime
from datetime import date, datetime

# импорт Decimal
from decimal import Decimal

# импорт Pydantic
from pydantic import BaseModel, ConfigDict, Field

# импорт enum
from app.schemas.enums import (
    CurrencyCodeEnum,
    SubscriptionStatusEnum,
    FreezeReason,
    CancellationReason,
)


# ==========================================================
# СХЕМА ОТВЕТА (ПОЛНАЯ)
# ==========================================================

class SubscriptionResponse(BaseModel):
    """Полная схема ответа по абонементу"""
    
    model_config = ConfigDict(from_attributes=True)

    # id абонемента
    id: UUID

    # id клиента
    client_id: UUID

    # id тарифа
    tariff_id: UUID

    # статус
    status: SubscriptionStatusEnum = Field(
        description="Статус абонемента",
        examples=["ACTIVE"],
    )

    # дата начала
    start_date: date = Field(
        description="Дата начала действия абонемента",
        examples=["2026-04-10"],
    )

    # дата окончания
    end_date: date = Field(
        description="Дата окончания действия абонемента",
        examples=["2026-05-10"],
    )

    # цена
    price: Decimal = Field(
        description="Зафиксированная цена абонемента",
        examples=[4500.00],
    )

    # валюта
    currency: CurrencyCodeEnum = Field(
        description="Валюта абонемента",
        examples=["RUB"],
    )

    # лимит посещений
    visit_limit: int | None = Field(
        default=None,
        description="Лимит посещений",
        examples=[8],
    )

    # использовано посещений
    visits_used: int = Field(
        description="Количество использованных посещений",
        examples=[0],
    )

    # безлимитный ли
    is_unlimited: bool = Field(
        description="Безлимитный ли абонемент",
        examples=[False],
    )

    # активен ли
    is_active: bool = Field(
        description="Активен ли абонемент",
        examples=[True],
    )

    # заметка
    notes: str | None = Field(
        default=None,
        description="Комментарий к абонементу",
        examples=["Первичная продажа"],
    )

    # ==========================================================
    # НОВЫЕ ПОЛЯ ДЛЯ ЖИЗНЕННОГО ЦИКЛА
    # ==========================================================

    # Заморозка
    frozen_at: datetime | None = Field(
        default=None,
        description="Дата заморозки абонемента",
    )
    frozen_until: date | None = Field(
        default=None,
        description="Дата окончания заморозки",
    )
    freeze_reason: str | None = Field(
        default=None,
        description="Причина заморозки",
    )

    # Продление и отмена
    auto_renew: bool = Field(
        default=False,
        description="Автоматическое продление",
    )
    cancelled_at: datetime | None = Field(
        default=None,
        description="Дата отмены абонемента",
    )
    cancellation_reason: str | None = Field(
        default=None,
        description="Причина отмены",
    )
    last_renewed_at: datetime | None = Field(
        default=None,
        description="Дата последнего продления",
    )

    # дата создания
    created_at: datetime

    # дата обновления
    updated_at: datetime


# ==========================================================
# СХЕМА ОТВЕТА ДЛЯ СПИСКА
# ==========================================================

class SubscriptionListResponse(BaseModel):
    """Схема ответа для списка абонементов"""
    
    items: list[SubscriptionResponse] = Field(
        description="Список абонементов"
    )
    count: int = Field(
        description="Количество абонементов"
    )


# ==========================================================
# СХЕМА СОЗДАНИЯ АБОНЕМЕНТА
# ==========================================================

class SubscriptionCreateRequest(BaseModel):
    """Схема запроса на создание абонемента"""
    
    client_id: UUID = Field(
        description="Идентификатор клиента",
    )
    tariff_id: UUID = Field(
        description="Идентификатор тарифа",
    )
    start_date: date = Field(
        description="Дата начала действия абонемента",
        examples=["2026-04-10"],
    )
    status: SubscriptionStatusEnum = Field(
        default=SubscriptionStatusEnum.ACTIVE,
        description="Статус абонемента",
        examples=["ACTIVE"],
    )
    auto_renew: bool = Field(
        default=False,
        description="Автоматическое продление",
    )
    notes: str | None = Field(
        default=None,
        description="Комментарий к созданию абонемента",
        examples=["Первичная продажа"],
    )


# ==========================================================
# СХЕМА ОБНОВЛЕНИЯ АБОНЕМЕНТА
# ==========================================================

class SubscriptionUpdateRequest(BaseModel):
    """Схема запроса на обновление абонемента"""
    
    status: SubscriptionStatusEnum | None = Field(
        default=None,
        description="Новый статус абонемента",
        examples=["FROZEN"],
    )
    start_date: date | None = Field(
        default=None,
        description="Новая дата начала",
        examples=["2026-04-12"],
    )
    end_date: date | None = Field(
        default=None,
        description="Новая дата окончания",
        examples=["2026-05-12"],
    )
    visits_used: int | None = Field(
        default=None,
        description="Новое количество использованных посещений",
        examples=[5],
    )
    auto_renew: bool | None = Field(
        default=None,
        description="Включить/выключить автопродление",
    )
    notes: str | None = Field(
        default=None,
        description="Новый комментарий",
        examples=["Заморозка по заявлению клиента"],
    )


# ==========================================================
# СХЕМЫ ДЛЯ ОПЕРАЦИЙ ЖИЗНЕННОГО ЦИКЛА
# ==========================================================

class FreezeSubscriptionRequest(BaseModel):
    """Схема запроса на заморозку абонемента"""
    
    frozen_until: date | None = Field(
        default=None,
        description="Дата окончания заморозки (если не указана — бессрочно)",
    )
    reason: FreezeReason = Field(
        default=FreezeReason.OTHER,
        description="Причина заморозки",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Дополнительные заметки",
    )


class UnfreezeSubscriptionRequest(BaseModel):
    """Схема запроса на разморозку абонемента"""
    
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Дополнительные заметки",
    )


class RenewSubscriptionRequest(BaseModel):
    """Схема запроса на продление абонемента"""
    
    auto_renew: bool | None = Field(
        default=None,
        description="Включить/выключить автопродление",
    )


class CancelSubscriptionRequest(BaseModel):
    """Схема запроса на отмену абонемента"""
    
    reason: CancellationReason = Field(
        default=CancellationReason.USER_REQUEST,
        description="Причина отмены",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Дополнительные заметки",
    )