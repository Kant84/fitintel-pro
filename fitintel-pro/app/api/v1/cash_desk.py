# app/api/v1/cash_desk.py

from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.cash_desk import (
    CashDeskOpenRequest,
    CashDeskCloseRequest,
    CashDeskSessionResponse,
    CashDeskSessionListResponse,
    CashDeskCurrentResponse,
    CashOperationCreateRequest,
    CashOperationResponse,
    CashOperationListResponse,
)
from app.services.cash_desk_service import CashDeskService


router = APIRouter(prefix="/cash-desk", tags=["Cash Desk"])


# ==========================================================
# УПРАВЛЕНИЕ СМЕНАМИ
# ==========================================================

@router.post("/open", response_model=CashDeskSessionResponse)
def open_session(
    payload: CashDeskOpenRequest,
    current_user: User = Depends(require_permission("cash_desk.open")),
    db: Session = Depends(get_db),
):
    """Открыть кассовую смену"""
    service = CashDeskService(db)
    session = service.open_session(
        cashier_user_id=str(current_user.id),
        opening_balance=payload.opening_balance,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )
    return service._build_session_response(session)


@router.post("/close", response_model=CashDeskSessionResponse)
def close_session(
    payload: CashDeskCloseRequest,
    current_user: User = Depends(require_permission("cash_desk.close")),
    db: Session = Depends(get_db),
):
    """Закрыть кассовую смену (Z-отчёт)"""
    service = CashDeskService(db)
    session = service.close_session(
        cashier_user_id=str(current_user.id),
        actual_cash=payload.actual_cash,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )
    return service._build_session_response(session)


@router.get("/current", response_model=CashDeskCurrentResponse)
def get_current_session(
    current_user: User = Depends(require_permission("cash_desk.read")),
    db: Session = Depends(get_db),
):
    """Получить текущую открытую смену"""
    service = CashDeskService(db)
    return service.get_current_session(str(current_user.id))


@router.get("/sessions", response_model=CashDeskSessionListResponse)
def list_sessions(
    cashier_user_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("cash_desk.read")),
    db: Session = Depends(get_db),
):
    """Получить список смен"""
    service = CashDeskService(db)
    return service.list_sessions(
        cashier_user_id=cashier_user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/sessions/{session_id}", response_model=CashDeskSessionResponse)
def get_session(
    session_id: UUID,
    current_user: User = Depends(require_permission("cash_desk.read")),
    db: Session = Depends(get_db),
):
    """Получить смену по ID"""
    service = CashDeskService(db)
    session = service.get_session(str(session_id))
    return service._build_session_response(session)


@router.get("/sessions/{session_id}/report")
def get_z_report(
    session_id: UUID,
    current_user: User = Depends(require_permission("cash_desk.read")),
    db: Session = Depends(get_db),
):
    """Получить Z-отчёт по смене"""
    service = CashDeskService(db)
    return service.get_z_report(str(session_id))


# ==========================================================
# КАССОВЫЕ ОПЕРАЦИИ
# ==========================================================

@router.post("/operation", response_model=CashOperationResponse)
def add_operation(
    payload: CashOperationCreateRequest,
    current_user: User = Depends(require_permission("cash_desk.manage")),
    db: Session = Depends(get_db),
):
    """Добавить кассовую операцию"""
    service = CashDeskService(db)
    operation = service.add_operation(
        cashier_user_id=str(current_user.id),
        operation_type=payload.operation_type,
        amount=payload.amount,
        payment_method=payload.payment_method,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        description=payload.description,
        actor_user_id=str(current_user.id),
    )
    return service._build_operation_response(operation)


@router.get("/sessions/{session_id}/operations", response_model=CashOperationListResponse)
def get_session_operations(
    session_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("cash_desk.read")),
    db: Session = Depends(get_db),
):
    """Получить операции смены"""
    service = CashDeskService(db)
    return service.get_session_operations(
        session_id=str(session_id),
        limit=limit,
        offset=offset,
    )


@router.post("/verify")
def verify_cash(
    actual_cash: Decimal = Query(gt=0, description="Фактическая наличность"),
    notes: str | None = None,
    current_user: User = Depends(require_permission("cash_desk.manage")),
    db: Session = Depends(get_db),
):
    """Промежуточная сверка наличных"""
    service = CashDeskService(db)
    return service.verify_cash(
        cashier_user_id=str(current_user.id),
        actual_cash=actual_cash,
        notes=notes,
        actor_user_id=str(current_user.id),
    )