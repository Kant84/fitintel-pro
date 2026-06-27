
# app/api/v1/sales.py

from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.sale import (
    SaleCreate,
    SaleResponse,
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


@router.get("/", response_model=list[SaleResponse])
async def list_sales(
    current_user: User = Depends(require_permission("sales.read")),
    db: Session = Depends(get_db),
):
    """Получить список продаж"""
    service = SaleService(db)
    # Заглушка — возвращаем пустой список
    return []

@router.post("/", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    sale_data: SaleCreate,
    current_user: User = Depends(require_permission("sales.create")),
    db: Session = Depends(get_db),
):
    """Создать продажу"""
    service = SaleService(db)
    # Получаем payment_methods если есть
    payment_methods = None
    if sale_data.payment_methods:
        payment_methods = [pm.model_dump() for pm in sale_data.payment_methods]
    
    sale = service.create_sale(
        cashier_id=current_user.id,
        items=[item.model_dump() for item in sale_data.items],
        payment_method=sale_data.payment_method,
        discount_code=sale_data.discount_code,
        payment_methods=payment_methods
    )
    return sale


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



@router.get("/terminal-status")
async def get_terminal_status(
    current_user: User = Depends(require_permission("sales.read")),
):
    """Проверить статус терминала"""
    from app.services.terminal_emulator import TerminalEmulator
    terminal = TerminalEmulator()
    return terminal.get_status()

@router.get("/report")
async def get_sales_report(
    date: str = "2026-06-27",
    current_user: User = Depends(require_permission("sales.read")),
    db: Session = Depends(get_db),
):
    """Отчёт по продажам за день"""
    from sqlalchemy import func
    from app.models.sale import Sale
    
    from datetime import datetime
    date_start = datetime.strptime(f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S")
    date_end = datetime.strptime(f"{date} 23:59:59", "%Y-%m-%d %H:%M:%S")
    
    total = db.query(func.sum(Sale.total_amount)).filter(
        Sale.created_at >= date_start,
        Sale.created_at < date_end
    ).scalar() or 0
    
    count = db.query(func.count(Sale.id)).filter(
        Sale.created_at >= date_start,
        Sale.created_at < date_end
    ).scalar() or 0
    
    return {"date": date, "total_amount": str(total), "count": count}

@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: UUID,
    current_user: User = Depends(require_permission("sales.read")),
    db: Session = Depends(get_db),
):
    """Получить продажу по ID"""
    from sqlalchemy import text
    from app.models.sale import Sale
    sale = db.query(Sale).filter(Sale.id == str(sale_id)).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Продажа не найдена")
    return sale

@router.post("/{sale_id}/refund")
async def refund_sale(
    sale_id: UUID,
    reason: str = "Возврат",
    current_user: User = Depends(require_permission("sales.refund")),
    db: Session = Depends(get_db),
):
    """Возврат продажи"""
    from sqlalchemy import text
    from app.models.sale import Sale
    from datetime import datetime, timedelta
    
    sale = db.query(Sale).filter(Sale.id == str(sale_id)).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Продажа не найдена")
    
    # Проверяем, что продажа не старше 24 часов
    from datetime import timezone
    if datetime.now(timezone.utc) - sale.created_at > timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Возврат возможен в течение 24 часов")
    
    sale.status = "REFUNDED"
    sale.refunded_at = datetime.now()
    db.commit()
    db.refresh(sale)
    return {"success": True, "message": "Продажа возвращена", "sale_id": str(sale_id)}



