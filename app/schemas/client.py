# app/schemas/client.py
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.schemas.enums import ClientStatus, GenderEnum, ClientCategoryEnum


# ---------------------------------------------------------------- helpers
_GENDER_ALIASES = {
    "мужской": "MALE", "м": "MALE", "male": "MALE",
    "женский": "FEMALE", "ж": "FEMALE", "female": "FEMALE",
    "не указан": "НЕ_УКАЗАН", "не_указан": "НЕ_УКАЗАН", "none": "НЕ_УКАЗАН",
}

import re as _re

_YEAR_2DIGIT = _re.compile(r"^\d{1,2}[-./]\d{1,2}[-./]\d{2}$")


def _norm_gender(v):
    """Принимает код enum, русскую подпись ('Мужской'), регистронезависимо."""
    if v is None or isinstance(v, GenderEnum):
        return v
    s = str(v).strip()
    if not s:
        return None
    return _GENDER_ALIASES.get(s.lower(), s)


def _norm_date(v):
    """дд-мм-гггг / дд.мм.гггг / дд/мм/гггг / ддммгггг → date (год СТРОГО 4 цифры).
    Двузначные года запрещены — понятная ошибка вместо угадывания века."""
    if v is None or isinstance(v, date):
        return v
    s = str(v).strip()
    if not s:
        return None
    # ISO уже в порядке
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    # двузначный год — сразу честная ошибка
    if _YEAR_2DIGIT.match(s):
        raise ValueError("Год должен быть четырёхзначным. Формат: ДД-ММ-ГГГГ")
    # варианты с разделителями: 01-02-1990, 01.02.1990, 01/02/1990
    m = _re.fullmatch(r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})", s)
    if m:
        d, mo, y = m.groups()
        try:
            return date(int(y), int(mo), int(d))
        except ValueError:
            return v            # отдадим на откуп pydantic — даст понятный 422
    # склейка: 01021990
    m = _re.fullmatch(r"(\d{2})(\d{2})(\d{4})", s)
    if m:
        d, mo, y = m.groups()
        try:
            return date(int(y), int(mo), int(d))
        except ValueError:
            return v
    return v                    # пусть pydantic сообщит об ошибке


class _ClientDatesMixin:
    @field_validator("birth_date", mode="before")
    @classmethod
    def _v_birth(cls, v):
        return _norm_date(v)


class _ClientGenderMixin:
    @field_validator("gender", mode="before")
    @classmethod
    def _v_gender(cls, v):
        return _norm_gender(v)


# схема ответа по клиенту
class ClientResponse(BaseModel):
    wallet_balance: float | None = None
    bonuses: float | None = None
    # разрешаем строить схему из ORM-объектов
    model_config = ConfigDict(from_attributes=True)

    # идентификатор клиента
    id: UUID

    # имя клиента
    first_name: str = Field(
        description="Имя клиента",
        examples=["Иван"],
    )

    # фамилия клиента
    last_name: str = Field(
        description="Фамилия клиента",
        examples=["Иванов"],
    )

    # отчество клиента
    middle_name: str | None = Field(
        default=None,
        description="Отчество клиента",
        examples=["Иванович"],
    )

    # телефон клиента
    phone: str = Field(
        description="Телефон клиента",
        examples=["+79991234567"],
    )

    # email клиента (может отсутствовать)
    email: str | None = Field(
        default=None,
        description="Email клиента",
        examples=["ivan@test.com"],
    )

    # пол клиента
    gender: GenderEnum = Field(
        default=GenderEnum.НЕ_УКАЗАН,
        description="Пол клиента",
        examples=["МУЖСКОЙ"],
    )

    # дата рождения клиента
    birth_date: date | None = Field(
        default=None,
        description="Дата рождения клиента",
        examples=["1990-05-17"],
    )

    # категория клиента
    client_category: ClientCategoryEnum = Field(
        default=ClientCategoryEnum.НЕ_УКАЗАНА,
        description="Категория клиента",
        examples=["ВЗРОСЛЫЙ"],
    )

    # статус клиента
    status: ClientStatus = Field(
        description="Статус клиента",
        examples=["ACTIVE"],
    )

    # активность клиента
    is_active: bool = Field(
        description="Активен ли клиент",
        examples=[True],
    )

    # дата создания
    created_at: datetime

    # дата обновления
    updated_at: datetime


# схема ответа для списка клиентов
class ClientListResponse(BaseModel):
    # список клиентов
    items: list[ClientResponse]

    # количество элементов
    count: int


# схема запроса на создание клиента
class ClientCreateRequest(_ClientDatesMixin, _ClientGenderMixin, BaseModel):
    # имя клиента
    first_name: str = Field(
        min_length=1,
        max_length=100,
        description="Имя клиента",
        examples=["Иван"],
    )

    # фамилия клиента
    last_name: str = Field(
        min_length=1,
        max_length=100,
        description="Фамилия клиента",
        examples=["Иванов"],
    )

    # отчество клиента
    middle_name: str | None = Field(
        default=None,
        max_length=100,
        description="Отчество клиента",
        examples=["Иванович"],
    )

    # телефон клиента
    phone: str = Field(
        min_length=5,
        max_length=50,
        description="Телефон клиента",
        examples=["+79991234567"],
    )

    # email клиента — НЕобязателен (в клубе не у всех есть почта)
    email: EmailStr | None = Field(
        default=None,
        description="Email клиента",
        examples=["ivan@test.com"],
    )

    # пол клиента: код enum или русская подпись («Мужской»)
    gender: GenderEnum | None = Field(
        default=None,
        description="Пол клиента",
        examples=["МУЖСКОЙ"],
    )

    # дата рождения: ISO или дд-мм-гггг / дд.мм.гггг / ддммгггг (год строго 4 цифры)
    birth_date: date | None = Field(
        default=None,
        description="Дата рождения клиента",
        examples=["1990-05-17"],
    )

    # категория клиента
    client_category: ClientCategoryEnum | None = Field(
        default=None,
        description="Категория клиента",
        examples=["ВЗРОСЛЫЙ"],
    )

    # статус клиента
    status: ClientStatus | None = Field(
        default=None,
        description="Статус клиента",
        examples=["ACTIVE"],
    )

    # флаг активности
    is_active: bool | None = Field(
        default=None,
        description="Признак активности клиента",
        examples=[True],
    )


# схема запроса на обновление клиента
class ClientUpdateRequest(_ClientDatesMixin, _ClientGenderMixin, BaseModel):
    # новое имя клиента
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Новое имя клиента",
        examples=["Пётр"],
    )

    # новая фамилия клиента
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Новая фамилия клиента",
        examples=["Петров"],
    )

    # новое отчество клиента
    middle_name: str | None = Field(
        default=None,
        max_length=100,
        description="Новое отчество клиента",
        examples=["Петрович"],
    )

    # новый телефон клиента
    phone: str | None = Field(
        default=None,
        min_length=5,
        max_length=50,
        description="Новый телефон клиента",
        examples=["+79990001122"],
    )

    # новый email клиента
    email: EmailStr | None = Field(
        default=None,
        description="Новый email клиента",
        examples=["new_email@test.com"],
    )

    # новый пол клиента
    gender: GenderEnum | None = Field(
        default=None,
        description="Новый пол клиента",
        examples=["ЖЕНСКИЙ"],
    )

    # новая дата рождения клиента
    birth_date: date | None = Field(
        default=None,
        description="Новая дата рождения клиента",
        examples=["1985-12-10"],
    )

    # новая категория клиента
    client_category: ClientCategoryEnum | None = Field(
        default=None,
        description="Новая категория клиента",
        examples=["ПЕНСИОНЕР"],
    )

    # новый статус клиента
    status: ClientStatus | None = Field(
        default=None,
        description="Новый статус клиента",
        examples=["BLOCKED"],
    )

    # новый флаг активности
    is_active: bool | None = Field(
        default=None,
        description="Новый признак активности клиента",
        examples=[False],
    )