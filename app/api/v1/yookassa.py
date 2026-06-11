# app/api/v1/yookassa.py
"""
YooKassa API — онлайн-платежи.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.yookassa_service import YooKassaService

router = APIRouter(prefix="/yookassa", tags=["YooKassa"])


class CreatePaymentRequest(BaseModel):
    amount: float
    description: str
    return_url: str
    client_email: Optional[str] = ""
    metadata: Optional[dict] = None


class RefundRequest(BaseModel):
    payment_id: str
    amount: float


def get_service(db: Session = Depends(get_db)) -> YooKassaService:
    return YooKassaService(db)


@router.post("/payments")
def create_payment(
    payload: CreatePaymentRequest,
    service: YooKassaService = Depends(get_service),
):
    """Создать платёж"""
    return service.create_payment(
        amount=payload.amount,
        description=payload.description,
        return_url=payload.return_url,
        client_email=payload.client_email,
        metadata=payload.metadata,
    )


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: str,
    service: YooKassaService = Depends(get_service),
):
    """Получить статус платежа"""
    return service.get_payment(payment_id)


@router.post("/payments/{payment_id}/cancel")
def cancel_payment(
    payment_id: str,
    service: YooKassaService = Depends(get_service),
):
    """Отменить платёж"""
    return service.cancel_payment(payment_id)


@router.post("/refunds")
def create_refund(
    payload: RefundRequest,
    service: YooKassaService = Depends(get_service),
):
    """Создать возврат"""
    return service.create_refund(payload.payment_id, payload.amount)


@router.post("/webhook")
def yookassa_webhook(
    request: Request,
    service: YooKassaService = Depends(get_service),
):
    """Webhook от YooKassa"""
    import json
    payload = json.loads(request.body())
    return service.handle_webhook(payload)
