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


@router.get("/visits")
def analytics_visits(
    date: str = "2026-06-27",
    date_from: str = None,
    date_to: str = None,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Посещаемость за день или период (E18.1, E18.2)"""
    service = AnalyticsService(db)
    return service.get_visits(date, date_from, date_to)

@router.get("/revenue")
def analytics_revenue(
    date: str = "2026-06-27",
    group_by: str = None,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Выручка за день (E18.3, E18.4)"""
    service = AnalyticsService(db)
    return service.get_revenue(date, group_by)

@router.get("/top-clients")
def analytics_top_clients(
    limit: int = 10,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Топ клиентов (E18.5)"""
    service = AnalyticsService(db)
    return service.get_top_clients(limit)

@router.get("/top-services")
def analytics_top_services(
    limit: int = 10,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Топ услуг (E18.6)"""
    service = AnalyticsService(db)
    return service.get_top_services(limit)

@router.get("/conversion")
def analytics_conversion(
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Конверсия абонементов (E18.7)"""
    service = AnalyticsService(db)
    return service.get_conversion()

@router.get("/churn")
def analytics_churn(
    days: int = 30,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Отток клиентов (E18.8)"""
    service = AnalyticsService(db)
    return service.get_churn(days)

@router.get("/peak-hours")
def analytics_peak_hours(
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Пиковые часы (E18.9)"""
    service = AnalyticsService(db)
    return service.get_peak_hours()

@router.get("/zone-occupancy")
def analytics_zone_occupancy(
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Загрузка зон (E18.10)"""
    service = AnalyticsService(db)
    return service.get_zone_occupancy()

@router.get("/report")
def analytics_report(
    format: str = "pdf",
    date_from: str = None,
    date_to: str = None,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Экспорт отчёта (E18.11, E18.12)"""
    service = AnalyticsService(db)
    return service.get_report(format, date_from, date_to)

@router.get("/compare")
def analytics_compare(
    period1: str = None,
    period2: str = None,
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Сравнение периодов (E18.13)"""
    service = AnalyticsService(db)
    return service.compare_periods(period1, period2)

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
