# app/api/v1/receipts.py

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.receipt import (
    ReceiptResponse,
    ReceiptSendRequest,
    ReceiptSendResponse,
)
from app.services.receipt_service import ReceiptService


router = APIRouter(prefix="/receipts", tags=["Receipts"])


@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(
    receipt_id: UUID,
    current_user=Depends(require_permission("receipts.read")),
    db: Session = Depends(get_db),
):
    """Получить чек по ID"""
    service = ReceiptService(db)
    receipt = service.get_receipt(str(receipt_id))
    return service._build_response(receipt)


@router.get("/payment/{payment_id}", response_model=ReceiptResponse)
def get_receipt_by_payment(
    payment_id: UUID,
    current_user=Depends(require_permission("receipts.read")),
    db: Session = Depends(get_db),
):
    """Получить чек по ID платежа"""
    service = ReceiptService(db)
    receipt = service.get_receipt_by_payment(str(payment_id))
    return service._build_response(receipt)


@router.get("/number/{receipt_number}", response_model=ReceiptResponse)
def get_receipt_by_number(
    receipt_number: str,
    current_user=Depends(require_permission("receipts.read")),
    db: Session = Depends(get_db),
):
    """Получить чек по номеру"""
    service = ReceiptService(db)
    receipt = service.get_receipt_by_number(receipt_number)
    return service._build_response(receipt)


@router.post("/{receipt_id}/send", response_model=ReceiptSendResponse)
def send_receipt(
    receipt_id: UUID,
    payload: ReceiptSendRequest,
    current_user=Depends(require_permission("receipts.send")),
    db: Session = Depends(get_db),
):
    """Отправить чек на email/SMS"""
    service = ReceiptService(db)
    return service.send_receipt(
        receipt_id=str(receipt_id),
        email=payload.email,
        phone=payload.phone,
        send_sms=payload.send_sms,
        actor_user_id=str(current_user.id),
    )


@router.get("/{receipt_id}/pdf")
def download_receipt_pdf(
    receipt_id: UUID,
    current_user=Depends(require_permission("receipts.read")),
    db: Session = Depends(get_db),
):
    """Скачать чек в PDF"""
    service = ReceiptService(db)
    pdf_content = service.generate_pdf(str(receipt_id))
    
    return StreamingResponse(
        iter([pdf_content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=receipt_{receipt_id}.pdf"},
    )


@router.post("/{receipt_id}/resend-fiscal")
def resend_fiscal_receipt(
    receipt_id: UUID,
    current_user=Depends(require_permission("receipts.send")),
    db: Session = Depends(get_db),
):
    """Повторно отправить чек в ОФД"""
    service = ReceiptService(db)
    receipt = service.resend_fiscal_receipt(
        receipt_id=str(receipt_id),
        actor_user_id=str(current_user.id),
    )
    return {"success": True, "receipt_id": receipt.id}
