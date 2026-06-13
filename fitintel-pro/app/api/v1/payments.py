# app/api/v1/payments.py

from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentResponse,
    PaymentListResponse,
    PaymentCreateRequest,
    PaymentRefundRequest,
    PaymentRefundResponse,
    PaymentOnlineResponse,
)
from app.schemas.enums import PaymentStatus
from app.services.payment_service import PaymentService


router = APIRouter(prefix="/payments", tags=["Payments"])


# ==========================================================
# ДЛЯ КЛИЕНТА
# ==========================================================

@router.get("/me", response_model=PaymentListResponse)
def get_my_payments(
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить свои платежи"""
    service = PaymentService(db)
    return service.get_client_payments(
        client_id=str(current_user.id),
        limit=limit,
        offset=offset,
        status_filter=status_filter.value if status_filter else None,
    )


# ==========================================================
# ДЛЯ АДМИНИСТРАТОРОВ
# ==========================================================

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreateRequest,
    current_user: User = Depends(require_permission("payments.create")),
    db: Session = Depends(get_db),
):
    """Создать платёж"""
    service = PaymentService(db)
    payment = service.create_payment(
        client_id=str(payload.client_id),
        amount=payload.amount,
        payment_method=payload.payment_method,
        payment_system=payload.payment_system,
        notes=payload.notes,
        return_url=payload.return_url,
        webhook_url=payload.webhook_url,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(payment)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: UUID,
    current_user: User = Depends(require_permission("payments.read")),
    db: Session = Depends(get_db),
):
    """Получить платёж по ID"""
    service = PaymentService(db)
    payment = service.get_payment(str(payment_id))
    return service._build_response(payment)


@router.get("/client/{client_id}", response_model=PaymentListResponse)
def get_client_payments(
    client_id: UUID,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("payments.read")),
    db: Session = Depends(get_db),
):
    """Получить платежи клиента"""
    service = PaymentService(db)
    return service.get_client_payments(
        client_id=str(client_id),
        limit=limit,
        offset=offset,
        status_filter=status_filter.value if status_filter else None,
    )


@router.post("/{payment_id}/complete", response_model=PaymentResponse)
def complete_payment(
    payment_id: UUID,
    current_user: User = Depends(require_permission("payments.update")),
    db: Session = Depends(get_db),
):
    """Подтвердить платёж"""
    service = PaymentService(db)
    payment = service.complete_payment(
        payment_id=str(payment_id),
        actor_user_id=str(current_user.id),
    )
    return service._build_response(payment)


@router.post("/{payment_id}/refund", response_model=PaymentRefundResponse)
def refund_payment(
    payment_id: UUID,
    payload: PaymentRefundRequest,
    current_user: User = Depends(require_permission("payments.refund")),
    db: Session = Depends(get_db),
):
    """Возврат платежа"""
    service = PaymentService(db)
    return service.refund_payment(
        payment_id=str(payment_id),
        amount=payload.amount,
        reason=payload.reason,
        refund_to_balance=payload.refund_to_balance,
        actor_user_id=str(current_user.id),
    )


@router.post("/online", response_model=PaymentOnlineResponse)
def create_online_payment(
    payload: PaymentCreateRequest,
    current_user: User = Depends(require_permission("payments.create")),
    db: Session = Depends(get_db),
):
    """Создать онлайн-платёж (карта, СБП)"""
    service = PaymentService(db)
    return service.create_online_payment(
        client_id=str(payload.client_id),
        amount=payload.amount,
        payment_method=payload.payment_method,
        return_url=payload.return_url,
        webhook_url=payload.webhook_url,
        actor_user_id=str(current_user.id),
    )


@router.post("/webhook/{payment_system}")
async def payment_webhook(
    payment_system: str,
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Webhook от платёжной системы.
    
    Публичный endpoint (без авторизации).
    """
    service = PaymentService(db)
    return service.handle_webhook(payment_system, request)