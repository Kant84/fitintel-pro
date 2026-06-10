# app/schemas/client_event.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# схема ответа для события клиента
class ClientEventResponse(BaseModel):
    # разрешаем строить схему из ORM-объектов
    model_config = ConfigDict(from_attributes=True)

    # идентификатор события
    id: UUID

    # идентификатор клиента
    client_id: UUID

    # тип события
    event_type: str = Field(
        description="Тип события клиента",
        examples=["КЛИЕНТ_СОЗДАН"],
    )

    # заголовок события
    title: str = Field(
        description="Краткий заголовок события",
        examples=["Клиент создан"],
    )

    # описание события
    description: str | None = Field(
        default=None,
        description="Подробное описание события",
        examples=["В CRM создана новая карточка клиента"],
    )

    # кто выполнил действие
    actor_user_id: UUID | None = Field(
        default=None,
        description="ID пользователя, который выполнил действие",
    )

    # дата события
    created_at: datetime


# схема ответа для списка событий клиента
class ClientEventListResponse(BaseModel):
    # список событий
    items: list[ClientEventResponse]

    # количество элементов
    count: int