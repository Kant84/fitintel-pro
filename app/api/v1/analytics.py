# app/api/v1/analytics.py
from datetime import date
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.analytics import (
    DashboardStats,
    ForecastRequest,
    ForecastResponse,
    RecalcResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardStats,
    status_code=status.HTTP_200_OK,
)
def analytics_dashboard(
    club_id: int = 1,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Сводка дашборда (E16)"""
    service = AnalyticsService(db)
    return service.dashboard(club_id)


@router.post(
    "/forecast",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
)
def analytics_forecast(
    payload: ForecastRequest,
    club_id: int = 1,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Прогноз на N дней (E16)"""
    service = AnalyticsService(db)
    return service.forecast(club_id, payload.metric, payload.days_ahead)


@router.post(
    "/recalc",
    response_model=RecalcResponse,
    status_code=status.HTTP_200_OK,
)
def analytics_recalc(
    club_id: int = 1,
    target_date: date | None = None,
    current_user=Depends(require_permission("analytics.update")),
    db: Session = Depends(get_db),
):
    """Ручной пересчёт агрегатов (E16)"""
    service = AnalyticsService(db)
    return service.recalc(club_id, target_date)
