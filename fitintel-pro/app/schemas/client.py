# app/schemas/client.py
# app/schemas/client.py

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.enums import ClientStatus, GenderEnum, ClientCategoryEnum


# схема ответа по клиенту
class ClientResponse(BaseModel):
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

    # email клиента
    email: str = Field(
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
class ClientCreateRequest(BaseModel):
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

    # email клиента
    email: EmailStr = Field(
        description="Email клиента",
        examples=["ivan@test.com"],
    )

    # пол клиента
    gender: GenderEnum | None = Field(
        default=None,
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
class ClientUpdateRequest(BaseModel):
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