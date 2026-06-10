# app/schemas/tariff.py

# импорт UUID
from uuid import UUID

# импорт datetime
from datetime import datetime

# импорт Decimal
from decimal import Decimal

# импорт Pydantic
from pydantic import BaseModel, ConfigDict, Field

# импорт enum валют
from app.schemas.enums import CurrencyCodeEnum


# схема ответа по тарифу
class TariffResponse(BaseModel):
    # разрешаем построение из ORM-объектов
    model_config = ConfigDict(from_attributes=True)

    # идентификатор тарифа
    id: UUID

    # код тарифа
    code: str = Field(
        description="Внутренний код тарифа",
        examples=["MONTH_8"],
    )

    # название тарифа
    name: str = Field(
        description="Название тарифа",
        examples=["8 посещений / 30 дней"],
    )

    # описание тарифа
    description: str | None = Field(
        default=None,
        description="Описание тарифа",
        examples=["Базовый месячный тариф"],
    )

    # цена тарифа
    price: Decimal = Field(
        description="Цена тарифа",
        examples=[3500.00],
    )

    # валюта тарифа
    currency: CurrencyCodeEnum = Field(
        description="Валюта тарифа",
        examples=["RUB"],
    )

    # длительность в днях
    duration_days: int = Field(
        description="Срок действия тарифа в днях",
        examples=[30],
    )

    # лимит посещений
    visit_limit: int | None = Field(
        default=None,
        description="Лимит посещений, если тариф не безлимитный",
        examples=[8],
    )

    # безлимитность
    is_unlimited: bool = Field(
        description="Безлимитный ли тариф",
        examples=[False],
    )

    # активность
    is_active: bool = Field(
        description="Активен ли тариф",
        examples=[True],
    )

    # дата создания
    created_at: datetime

    # дата обновления
    updated_at: datetime


# схема ответа списка тарифов
class TariffListResponse(BaseModel):
    # список тарифов
    items: list[TariffResponse]

    # количество элементов
    count: int


# схема создания тарифа
class TariffCreateRequest(BaseModel):
    # код тарифа
    code: str = Field(
        min_length=1,
        max_length=100,
        description="Внутренний код тарифа",
        examples=["MONTH_8"],
    )

    # название тарифа
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Название тарифа",
        examples=["8 посещений / 30 дней"],
    )

    # описание тарифа
    description: str | None = Field(
        default=None,
        description="Описание тарифа",
        examples=["Базовый месячный тариф"],
    )

    # цена тарифа
    price: Decimal = Field(
        description="Цена тарифа",
        examples=[3500.00],
    )

    # валюта
    currency: CurrencyCodeEnum = Field(
        default=CurrencyCodeEnum.RUB,
        description="Валюта тарифа",
        examples=["RUB"],
    )

    # срок действия в днях
    duration_days: int = Field(
        description="Срок действия тарифа в днях",
        examples=[30],
    )

    # лимит посещений
    visit_limit: int | None = Field(
        default=None,
        description="Лимит посещений",
        examples=[8],
    )

    # безлимитный ли тариф
    is_unlimited: bool = Field(
        default=False,
        description="Безлимитный ли тариф",
        examples=[False],
    )

    # активен ли тариф
    is_active: bool = Field(
        default=True,
        description="Активен ли тариф",
        examples=[True],
    )


# схема обновления тарифа
class TariffUpdateRequest(BaseModel):
    # новый код
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Новый внутренний код тарифа",
        examples=["MONTH_UNLIMITED"],
    )

    # новое название
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Новое название тарифа",
        examples=["Безлимит / 30 дней"],
    )

    # новое описание
    description: str | None = Field(
        default=None,
        description="Новое описание тарифа",
        examples=["Обновлённый тариф"],
    )

    # новая цена
    price: Decimal | None = Field(
        default=None,
        description="Новая цена тарифа",
        examples=[4200.00],
    )

    # новая валюта
    currency: CurrencyCodeEnum | None = Field(
        default=None,
        description="Новая валюта тарифа",
        examples=["RUB"],
    )

    # новый срок действия
    duration_days: int | None = Field(
        default=None,
        description="Новый срок действия в днях",
        examples=[60],
    )

    # новый лимит посещений
    visit_limit: int | None = Field(
        default=None,
        description="Новый лимит посещений",
        examples=[12],
    )

    # новый флаг безлимитности
    is_unlimited: bool | None = Field(
        default=None,
        description="Новый флаг безлимитности",
        examples=[True],
    )

    # новый флаг активности
    is_active: bool | None = Field(
        default=None,
        description="Новый флаг активности",
        examples=[False],
    )