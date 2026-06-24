from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import PaymentExportRequest
from app.services.report_service import ReportService

router = APIRouter()


@router.post("/visits/export")
def export_visits(
    request: PaymentExportRequest,
    current_user: User = Depends(require_permission("reports.export")),
    db: Session = Depends(get_db),
):
    """Экспорт посещений в XLSX/CSV"""
    service = ReportService(db)
    
    if request.format == "xlsx":
        output = service.export_visits_xlsx(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
        )
        
        filename = f"visits_report_{date.today().strftime('%Y%m%d')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    elif request.format == "csv":
        output = service.export_visits_csv(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
        )
        
        filename = f"visits_report_{date.today().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format for visits: {request.format}",
        )


@router.post("/payments/export")
def export_payments(
    request: PaymentExportRequest,
    current_user: User = Depends(require_permission("reports.export")),
    db: Session = Depends(get_db),
):
    """Экспорт платежей в XLSX/CSV/PDF"""
    service = ReportService(db)
    
    if request.format == "xlsx":
        output = service.export_payments_xlsx(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
            payment_direction=request.payment_direction,
            payment_category=request.payment_category,
            status=request.status,
        )
        
        filename = f"payments_report_{date.today().strftime('%Y%m%d')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    elif request.format == "csv":
        output = service.export_payments_csv(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
            payment_direction=request.payment_direction,
            payment_category=request.payment_category,
            status=request.status,
        )
        
        filename = f"payments_report_{date.today().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    elif request.format == "pdf":
        output = service.export_payments_pdf(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
            payment_direction=request.payment_direction,
            payment_category=request.payment_category,
            status=request.status,
        )
        
        filename = f"payments_report_{date.today().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    elif request.format == "1c":
        output = service.export_payments_1c(
            date_from=request.date_from,
            date_to=request.date_to,
        )
        
        filename = f"payments_1c_{date.today().strftime('%Y%m%d')}.txt"
        
        return StreamingResponse(
            output,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {request.format}",
        )
