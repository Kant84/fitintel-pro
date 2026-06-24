# Создаём схему отчётов
with open('app/schemas/report.py', 'w', encoding='utf-8') as f:
    f.write('''from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PaymentExportRequest(BaseModel):
    """Запрос на экспорт платежей"""
    
    date_from: Optional[date] = Field(
        default=None,
        description="Дата начала периода (YYYY-MM-DD)",
    )
    date_to: Optional[date] = Field(
        default=None,
        description="Дата окончания периода (YYYY-MM-DD)",
    )
    client_id: Optional[str] = Field(
        default=None,
        description="ID клиента (фильтр по клиенту)",
    )
    payment_direction: Optional[str] = Field(
        default=None,
        description="Направление: INCOME, EXPENSE",
    )
    payment_category: Optional[str] = Field(
        default=None,
        description="Категория: SUBSCRIPTION, SALARY, INVENTORY, RENT, UTILITIES, OTHER",
    )
    status: Optional[str] = Field(
        default=None,
        description="Статус: PENDING, COMPLETED, CANCELLED, REFUNDED",
    )
    format: str = Field(
        default="xlsx",
        description="Формат: xlsx, csv, pdf",
    )
''')

print("report.py создан!")

# Создаём router
with open('app/api/v1/reports.py', 'w', encoding='utf-8') as f:
    f.write('''from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.report import PaymentExportRequest
from app.services.report_service import ReportService

router = APIRouter()


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
        # TODO: CSV export
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="CSV export not yet implemented",
        )
    
    elif request.format == "pdf":
        # TODO: PDF export
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export not yet implemented",
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {request.format}",
        )
''')

print("reports.py создан!")
