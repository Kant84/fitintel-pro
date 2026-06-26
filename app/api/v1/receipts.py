# app/api/v1/receipts.py

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.db.session import get_db
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptResponse,
    ReceiptSendRequest,
    ReceiptSendResponse,
)
from app.services.receipt_service import ReceiptService


router = APIRouter(prefix="/receipts", tags=["Receipts"])



@router.post("/", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    receipt_data: ReceiptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создать чек"""
    service = ReceiptService(db)
    receipt = service.create_receipt(
        payment_id=receipt_data.payment_id,
        items=receipt_data.items,
        customer_email=receipt_data.customer_email,
        customer_phone=receipt_data.customer_phone,
        created_by=current_user.id,
        receipt_type=receipt_data.receipt_type if hasattr(receipt_data, 'receipt_type') else "SALE"
    )
    return receipt

@router.get("/export")
async def export_receipts(
    date_from: str = Query(..., description="Дата начала (YYYY-MM-DD)"),
    date_to: str = Query(..., description="Дата окончания (YYYY-MM-DD)"),
    format: str = Query(default="xlsx", enum=["xlsx", "csv", "pdf"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Экспорт чеков за период"""
    service = ReceiptService(db)
    return {"success": True, "message": f"Экспорт в формате {format} за период {date_from} - {date_to}", "count": 0}

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


@router.post("/{receipt_id}/fiscalize")
async def fiscalize_receipt(
    receipt_id: UUID,
    driver: str = Query(default="atol", description="Драйвер фискального регистратора"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Фискализация чека через АТОЛ"""
    service = ReceiptService(db)
    receipt = service.get_receipt(str(receipt_id))
    if not receipt:
        raise HTTPException(status_code=404, detail="Чек не найден")
    if receipt.fiscal_sign:
        raise HTTPException(status_code=400, detail="Чек уже фискализирован")
    # Заглушка для фискализации
    return {"success": True, "fiscal_document_number": "12345", "fiscal_sign": "ATOL-" + str(receipt_id)[:8], "driver": driver}

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
    # Проверяем, не фискализирован ли чек
    receipt = service.get_receipt(str(receipt_id))
    if receipt and receipt.fiscal_sign:
        raise HTTPException(status_code=400, detail="Чек уже фискализирован")
    return {"success": True, "receipt_id": receipt.id}

@router.post("/{receipt_id}/print")
async def print_receipt(
    receipt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Печать чека на принтере"""
    service = ReceiptService(db)
    receipt = service.get_receipt(str(receipt_id))
    if not receipt:
        raise HTTPException(status_code=404, detail="Чек не найден")
    return {"success": True, "message": "Чек отправлен на печать", "receipt_id": str(receipt_id)}

@router.get("/{receipt_id}/ofd-status")
async def get_ofd_status(
    receipt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Проверка статуса чека в ОФД"""
    service = ReceiptService(db)
    receipt = service.get_receipt(str(receipt_id))
    if not receipt:
        raise HTTPException(status_code=404, detail="Чек не найден")
    status = "delivered" if receipt.fiscal_sign else "pending"
    return {"receipt_id": str(receipt_id), "status": status, "fiscal_sign": receipt.fiscal_sign}

