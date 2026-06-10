# app/api/v1/clients.py

# импорт UUID для типизации идентификаторов клиентов
from uuid import UUID

# импорт FastAPI-инструментов
from fastapi import APIRouter, Depends, Query, status

# импорт SQLAlchemy Session
from sqlalchemy.orm import Session

# импорт зависимостей безопасности
from app.api.dependencies import require_permission

# импорт функции получения сессии базы данных
from app.db.session import get_db

# импорт схем клиентов
from app.schemas.client import (
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
)

# импорт сервиса клиентов
from app.services.client_service import ClientService


# создаём роутер clients
router = APIRouter(prefix="/clients", tags=["Clients"])


# ============================================================
# Получить список клиентов
# ============================================================
@router.get("/", response_model=ClientListResponse)
def list_clients(
    # смещение для пагинации
    offset: int = Query(default=0, ge=0),

    # лимит элементов
    limit: int = Query(default=100, ge=1, le=200),

    # проверяем право чтения клиентов
    current_user=Depends(require_permission("clients.read")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # получаем список клиентов
    clients = client_service.list_clients(
        offset=offset,
        limit=limit,
        actor_user_id=current_user.id,
    )

    # возвращаем готовый ответ
    return client_service.build_client_list_response(clients)


# ============================================================
# Получить клиента по UUID
# ============================================================
@router.get("/{client_id}", response_model=ClientResponse)
def get_client_by_id(
    # UUID клиента из URL
    client_id: UUID,

    # проверяем право чтения клиентов
    current_user=Depends(require_permission("clients.read")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # получаем клиента
    client = client_service.get_client_by_id(str(client_id))

    # пишем audit чтения карточки клиента
    client_service.audit.log(
        action="crm.client.read",
        status="success",
        actor_user_id=current_user.id,
        entity_type="client",
        entity_id=client.id,
        message="Client card requested",
        after_data={
            "client_id": client.id,
        },
    )

    # возвращаем клиента
    return client_service.build_client_response(client)


# ============================================================
# Создать клиента
# ============================================================
@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    # тело запроса
    payload: ClientCreateRequest,

    # проверяем право создания клиентов
    current_user=Depends(require_permission("clients.create")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # создаём клиента
    client = client_service.create_client(
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        phone=payload.phone,
        email=payload.email,
        gender=payload.gender.value if payload.gender else None,
        birth_date=payload.birth_date,
        client_category=payload.client_category.value if payload.client_category else None,
        status_value=payload.status.value if payload.status else None,
        is_active=payload.is_active,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return client_service.build_client_response(client)


# ============================================================
# Обновить клиента
# ============================================================
@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    # UUID клиента из URL
    client_id: UUID,

    # тело запроса
    payload: ClientUpdateRequest,

    # проверяем право изменения клиентов
    current_user=Depends(require_permission("clients.update")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # обновляем клиента
    client = client_service.update_client(
        client_id=str(client_id),
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        phone=payload.phone,
        email=payload.email,
        gender=payload.gender.value if payload.gender else None,
        birth_date=payload.birth_date,
        client_category=payload.client_category.value if payload.client_category else None,
        status_value=payload.status.value if payload.status else None,
        is_active=payload.is_active,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return client_service.build_client_response(client)