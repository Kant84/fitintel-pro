
# app/api/v1/sales.py

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.sale import (
    SaleSubscriptionRequest,
    SaleSubscriptionResponse,
    SaleServiceRequest,
    SaleServiceResponse,
    SaleVisitRequest,
    SaleVisitResponse,
    SalePackageRequest,
    SalePackageResponse,
)
from app.services.sale_service import SaleService


router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post("/subscription", response_model=SaleSubscriptionResponse)
def sell_subscription(
    payload: SaleSubscriptionRequest,
    current_user: User = Depends(require_permission("sales.create")),
    db: Session = Depends(get_db),
):
    """Продажа абонемента"""
    service = SaleService(db)
    return service.sell_subscription(payload, actor_user_id=str(current_user.id))


@router.post("/service", response_model=SaleServiceResponse)
def sell_service(
    payload: SaleServiceRequest,
    current_user: User = Depends(require_permission("sales.create")),
    db: Session = Depends(get_db),
):
    """Продажа дополнительной услуги"""
    service = SaleService(db)
    return service.sell_service(payload, actor_user_id=str(current_user.id))


@router.post("/visit", response_model=SaleVisitResponse)
def sell_visit(
    payload: SaleVisitRequest,
    current_user: User = Depends(require_permission("sales.create")),
    db: Session = Depends(get_db),
):
    """Продажа разового посещения"""
    service = SaleService(db)
    return service.sell_visit(payload, actor_user_id=str(current_user.id))


@router.post("/package", response_model=SalePackageResponse)
def sell_package(
    payload: SalePackageRequest,
    current_user: User = Depends(require_permission("sales.create")),
    db: Session = Depends(get_db),
):
    """
    Комплексная продажа (несколько товаров одним чеком).
    
    Пример тела запроса:
    {
        "client_id": "uuid",
        "payment_method": "CARD",
        "items": [
            {"type": "subscription", "tariff_id": "uuid", "quantity": 1},
            {"type": "service", "service_id": "uuid", "quantity": 2},
            {"type": "visit", "zone": "GYM", "quantity": 1}
        ],
        "notes": "Комплексная продажа"
    }
    """
    service = SaleService(db)
    
    # Преобразуем items в список словарей
    items_list = []
    for item in payload.items:
        item_dict = item.model_dump(exclude_none=True)
        items_list.append(item_dict)
    
    return service.sell_package(
        client_id=str(payload.client_id),
        items=items_list,
        payment_method=payload.payment_method,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )
