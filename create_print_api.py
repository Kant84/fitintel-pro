# create_print_api.py
with open('app/api/v1/print.py', 'w', encoding='utf-8') as f:
    f.write('''from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.user import User
from app.services.print_service import PrintService

router = APIRouter()


class PrintReceiptRequest(BaseModel):
    """Запрос на печать чека"""
    payment_id: str = Field(description="ID платежа")
    copies: int = Field(default=1, ge=1, le=10, description="Количество копий")


class PrintReportRequest(BaseModel):
    """Запрос на печать выписки"""
    payment_ids: List[str] = Field(description="Список ID платежей")
    copies: int = Field(default=1, ge=1, le=10, description="Количество копий")


class PrintJobResponse(BaseModel):
    """Ответ с заданием на печать"""
    id: str
    document_type: str
    status: str
    copies: int
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/devices")
def get_devices(
    device_type: Optional[str] = None,
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Получить список устройств"""
    service = PrintService(db)
    devices = service.get_devices(device_type=device_type)
    return [{"id": str(d.id), "name": d.name, "type": d.device_type, "status": d.status, "is_default": d.is_default} for d in devices]


@router.post("/receipt", response_model=PrintJobResponse)
def print_receipt(
    request: PrintReceiptRequest,
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Печать чека по платежу"""
    service = PrintService(db)
    try:
        job = service.print_receipt(
            payment_id=request.payment_id,
            actor_user_id=str(current_user.id),
        )
        return {
            "id": str(job.id),
            "document_type": job.document_type,
            "status": job.status,
            "copies": job.copies,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/report", response_model=PrintJobResponse)
def print_report(
    request: PrintReportRequest,
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Печать выписки по платежам"""
    service = PrintService(db)
    job = service.print_payment_report(
        payment_ids=request.payment_ids,
        actor_user_id=str(current_user.id),
    )
    return {
        "id": str(job.id),
        "document_type": job.document_type,
        "status": job.status,
        "copies": job.copies,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.get("/jobs")
def get_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Получить задания на печать"""
    service = PrintService(db)
    jobs = service.get_print_jobs(status=status, limit=limit)
    return [{
        "id": str(j.id),
        "document_type": j.document_type,
        "status": j.status,
        "copies": j.copies,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    } for j in jobs]


@router.post("/jobs/{job_id}/complete")
def complete_job(
    job_id: str,
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Отметить задание как выполненное"""
    service = PrintService(db)
    try:
        job = service.mark_job_completed(job_id)
        return {"id": str(job.id), "status": job.status, "printed_at": job.printed_at.isoformat() if job.printed_at else None}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
''')

print("print.py создан!")
