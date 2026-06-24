# app/api/v1/subscription_lifecycle.py

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.subscription import (
    SubscriptionResponse,
    FreezeSubscriptionRequest,
    RenewSubscriptionRequest,
    CancelSubscriptionRequest,
)
from app.schemas.subscription_event import SubscriptionEventListResponse
from app.services.subscription_lifecycle_service import SubscriptionLifecycleService

router = APIRouter(prefix="/subscriptions", tags=["Subscription Lifecycle"])


# ==========================================================
# ЗАМОРОЗКА
# ==========================================================

@router.post(
    "/{subscription_id}/freeze",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def freeze_subscription(
    subscription_id: UUID,
    payload: FreezeSubscriptionRequest,
    current_user=Depends(require_permission("subscriptions.update")),
    db: Session = Depends(get_db),
):
    """
    Заморозить абонемент.
    
    - Только активный абонемент можно заморозить
    - Указывается дата окончания заморозки (опционально)
    - На время заморозки дни не сгорают
    """
    service = SubscriptionLifecycleService(db)
    return service.freeze(
        subscription_id=str(subscription_id),
        frozen_until=payload.frozen_until,
        reason=payload.reason.value,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )


# ==========================================================
# РАЗМОРОЗКА
# ==========================================================

@router.post(
    "/{subscription_id}/unfreeze",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def unfreeze_subscription(
    subscription_id: UUID,
    current_user=Depends(require_permission("subscriptions.update")),
    db: Session = Depends(get_db),
):
    """
    Разморозить абонемент.
    
    - Только замороженный абонемент можно разморозить
    - Дата окончания сдвигается на количество замороженных дней
    """
    service = SubscriptionLifecycleService(db)
    return service.unfreeze(
        subscription_id=str(subscription_id),
        actor_user_id=str(current_user.id),
    )


# ==========================================================
# ПРОДЛЕНИЕ
# ==========================================================

@router.post(
    "/{subscription_id}/renew",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def renew_subscription(
    subscription_id: UUID,
    payload: RenewSubscriptionRequest,
    current_user=Depends(require_permission("subscriptions.update")),
    db: Session = Depends(get_db),
):
    """
    Продлить абонемент.
    
    - Можно продлить активный, истекший или замороженный абонемент
    - Если абонемент замёрз — сначала размораживается
    - Новая дата окончания = текущая + длительность тарифа
    """
    service = SubscriptionLifecycleService(db)
    return service.renew(
        subscription_id=str(subscription_id),
        auto_renew=payload.auto_renew,
        actor_user_id=str(current_user.id),
    )


# ==========================================================
# ОТМЕНА
# ==========================================================

@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def cancel_subscription(
    subscription_id: UUID,
    payload: CancelSubscriptionRequest,
    current_user=Depends(require_permission("subscriptions.update")),
    db: Session = Depends(get_db),
):
    """
    Отменить абонемент.
    
    - Можно отменить активный или замороженный абонемент
    - После отмены доступ закрывается
    """
    service = SubscriptionLifecycleService(db)
    return service.cancel(
        subscription_id=str(subscription_id),
        reason=payload.reason.value,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )


# ==========================================================
# ИСТОРИЯ СТАТУСОВ
# ==========================================================

@router.get(
    "/{subscription_id}/history",
    response_model=SubscriptionEventListResponse,
    status_code=status.HTTP_200_OK,
)
def get_subscription_history(
    subscription_id: UUID,
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
):
    """
    Получить историю изменений статуса абонемента.
    
    Возвращает все события жизненного цикла:
    - создание
    - заморозка/разморозка
    - продление
    - отмена
    - истечение срока
    """
    service = SubscriptionLifecycleService(db)
    return service.get_status_history(str(subscription_id), limit, offset)
