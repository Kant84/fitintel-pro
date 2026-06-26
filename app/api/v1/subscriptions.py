# app/api/v1/subscriptions.py

# импорт UUID
from uuid import UUID

# импорт FastAPI
from fastapi import APIRouter, Depends, Query, status, HTTPException

# импорт Session
from sqlalchemy.orm import Session

# импорт зависимостей
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User

# импорт get_db
from app.db.session import get_db

# импорт схем
from app.schemas.subscription import (
    SubscriptionCreateRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)

# импорт сервиса
from app.services.subscription_service import SubscriptionService


# создаём роутер
router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# список абонементов
@router.get("/", response_model=SubscriptionListResponse)
def list_subscriptions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user=Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    subscription_service = SubscriptionService(db)

    # получаем список
    subscriptions = subscription_service.list_subscriptions(
        offset=offset,
        limit=limit,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return subscription_service.build_subscription_list_response(subscriptions)


# получить абонемент по id
@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription_by_id(
    subscription_id: UUID,
    current_user=Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    subscription_service = SubscriptionService(db)

    # получаем объект
    subscription = subscription_service.get_subscription_by_id(str(subscription_id))

    # пишем аудит чтения
    subscription_service.audit.log(
        action="crm.subscription.read",
        status="success",
        actor_user_id=current_user.id,
        entity_type="subscription",
        entity_id=subscription.id,
        message="Subscription card requested",
        after_data={
            "subscription_id": subscription.id,
        },
    )

    # возвращаем ответ
    return subscription_service.build_subscription_response(subscription)


# создать абонемент
@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreateRequest,
    current_user=Depends(require_permission("subscriptions.create")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    subscription_service = SubscriptionService(db)

    # создаём абонемент
    subscription = subscription_service.create_subscription(
        client_id=str(payload.client_id),
        tariff_id=str(payload.tariff_id),
        start_date=payload.start_date,
        status_value=payload.status,
        notes=payload.notes,
        actor_user_id=current_user.id,
        time_restriction_type=payload.time_restriction_type,
        allowed_start_time=payload.allowed_start_time,
        allowed_end_time=payload.allowed_end_time,
    )

    # возвращаем ответ
    return subscription_service.build_subscription_response(subscription)


# обновить абонемент
@router.patch("/{subscription_id}", response_model=SubscriptionResponse)


# продление абонемента
@router.post("/{subscription_id}/extend", response_model=SubscriptionResponse)
def extend_subscription(
    subscription_id: UUID,
    days: int = Query(default=30, ge=1, description='Количество дней для продления'),
    current_user=Depends(require_permission('subscriptions.renew')),
    db: Session = Depends(get_db),
):
    """Продлить абонемент на указанное количество дней"""
    # создаём сервис
    subscription_service = SubscriptionService(db)
    
    # проверяем, не отменена ли подписка
    existing = subscription_service.get_subscription_by_id(str(subscription_id))
    if existing and existing.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Невозможно продлить отменённую подписку")
    
    # продлеваем абонемент
    subscription = subscription_service.extend_subscription(
        subscription_id=str(subscription_id),
        days=days,
        actor_user_id=current_user.id,
    )
    
    return subscription

def update_subscription(
    subscription_id: UUID,
    payload: SubscriptionUpdateRequest,
    current_user=Depends(require_permission("subscriptions.update")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    subscription_service = SubscriptionService(db)

    # обновляем абонемент
    subscription = subscription_service.update_subscription(
        subscription_id=str(subscription_id),
        status_value=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        visits_used=payload.visits_used,
        notes=payload.notes,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return subscription_service.build_subscription_response(subscription)

@router.get("/client/{client_id}", response_model=SubscriptionListResponse)
async def get_client_subscriptions(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить подписки клиента"""
    service = SubscriptionService(db)
    subscriptions = service.get_client_subscriptions(client_id=client_id)
    return {"items": subscriptions, "count": len(subscriptions)}

@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: UUID,
    current_user=Depends(require_permission('subscriptions.delete')),
    db: Session = Depends(get_db),
):
    """Удалить подписку"""
    service = SubscriptionService(db)
    subscription = service.get_subscription_by_id(str(subscription_id))
    if not subscription:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    db.delete(subscription)
    db.commit()
    return None

