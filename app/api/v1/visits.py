# app/api/v1/visits.py

from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.visit import (
    VisitResponse,
    VisitListResponse,
    VisitStatsResponse,
    VisitEntryRequest,
    VisitExitRequest,
    VisitCompleteRequest,
    ManualVisitRequest,
    VisitDeleteRequest,
    ActiveVisitsResponse,
)
from app.schemas.enums import VisitStatus
from app.services.visit_service import VisitService


router = APIRouter(prefix="/visits", tags=["Visits"])


# ==========================================================
# ОСНОВНЫЕ ОПЕРАЦИИ
# ==========================================================

@router.post(
    "/entry",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
)
def entry(
    payload: VisitEntryRequest,
    current_user=Depends(require_permission("visits.create")),
    db: Session = Depends(get_db),
):
    """
    Зафиксировать вход клиента.
    
    - Создаёт новое посещение
    - Списывает один визит из абонемента (если есть)
    - Проверяет лимиты и срок действия
    """
    service = VisitService(db)
    visit = service.entry(
        client_id=str(payload.client_id),
        subscription_id=str(payload.subscription_id) if payload.subscription_id else None,
        access_method=payload.access_method,
        access_device_id=payload.access_device_id,
        zone=payload.zone,
        entry_time=payload.entry_time,
        
        actor_user_id=str(current_user.id),
    )
    return service._build_response(visit)


@router.post(
    "/exit",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def exit(
    payload: VisitExitRequest,
    current_user=Depends(require_permission("visits.update")),
    db: Session = Depends(get_db),
):
    """
    Зафиксировать выход клиента.
    
    - Завершает активное посещение
    - Рассчитывает длительность пребывания
    """
    service = VisitService(db)
    visit = service.exit(
        visit_id=str(payload.visit_id),
        exit_time=payload.exit_time,
        
        actor_user_id=str(current_user.id),
    )
    return service._build_response(visit)


@router.post(
    "/{visit_id}/complete",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def complete_visit(
    visit_id: UUID,
    payload: VisitCompleteRequest,
    current_user=Depends(require_permission("visits.update")),
    db: Session = Depends(get_db),
):
    """
    Принудительно закрыть посещение (если не зафиксирован выход).
    """
    service = VisitService(db)
    visit = service.exit(
        visit_id=str(visit_id),
        exit_time=payload.exit_time,
        
        actor_user_id=str(current_user.id),
    )
    return service._build_response(visit)


# ==========================================================
# РУЧНЫЕ ОПЕРАЦИИ (ДЛЯ МЕНЕДЖЕРОВ)
# ==========================================================

@router.post(
    "/manual",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
)
def manual_add_visit(
    payload: ManualVisitRequest,
    current_user=Depends(require_permission("visits.create")),
    db: Session = Depends(get_db),
):
    """
    Ручное добавление посещения (менеджером).
    
    - Можно добавить посещение задним числом
    - Можно указать время входа и выхода
    """
    service = VisitService(db)
    visit = service.manual_add(
        data=payload,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(visit)


@router.delete(
    "/{visit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_visit(
    visit_id: UUID,
    payload: VisitDeleteRequest,
    current_user=Depends(require_permission("visits.delete")),
    db: Session = Depends(get_db),
):
    """
    Отменить посещение.
    
    - Меняет статус на CANCELLED
    - Не удаляет запись из БД (soft delete)
    """
    service = VisitService(db)
    service.cancel(
        visit_id=str(visit_id),
        reason=payload.reason,
        actor_user_id=str(current_user.id),
    )
    return None


# ==========================================================
# ПОЛУЧЕНИЕ ДАННЫХ
# ==========================================================

@router.get(
    "/{visit_id}",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def get_visit(
    visit_id: UUID,
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Получить информацию о посещении по ID"""
    service = VisitService(db)
    visit = service.get_visit(str(visit_id))
    return service._build_response(visit)


@router.get(
    "/client/{client_id}",
    response_model=VisitListResponse,
    status_code=status.HTTP_200_OK,
)
def get_client_visits(
    client_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: VisitStatus | None = Query(default=None, alias="status"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """
    Получить историю посещений клиента.
    
    - Поддерживает пагинацию
    - Можно фильтровать по статусу
    """
    service = VisitService(db)
    return service.get_client_visits(
        client_id=str(client_id),
        limit=limit,
        offset=offset,
        status=status_filter.value if status_filter else None,
    )


@router.get(
    "/active",
    response_model=VisitListResponse,
    status_code=status.HTTP_200_OK,
)
def get_active_visits(
    zone: str | None = Query(default=None, description="Фильтр по зоне"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """
    Получить список активных посещений (клиенты в клубе).
    
    - Возвращает всех клиентов, которые сейчас в клубе
    - Можно отфильтровать по зоне
    """
    service = VisitService(db)
    return service.get_active_visits(zone=zone)


@router.get(
    "/active/count",
    status_code=status.HTTP_200_OK,
)
def get_active_count(
    zone: str | None = Query(default=None, description="Фильтр по зоне"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """
    Получить количество клиентов в клубе.
    """
    service = VisitService(db)
    count = service.get_active_count(zone=zone)
    return {"count": count, "zone": zone}


# ==========================================================
# СТАТИСТИКА
# ==========================================================

@router.get(
    "/stats",
    response_model=VisitStatsResponse,
    status_code=status.HTTP_200_OK,
)
def get_visits_stats(
    period: str = Query(
        default="day",
        description="Период: day, week, month, year",
        pattern="^(day|week|month|year)$",
    ),
    start_date: date = Query(description="Дата начала"),
    end_date: date | None = Query(default=None, description="Дата окончания"),
    zone: str | None = Query(default=None, description="Фильтр по зоне"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """
    Получить статистику посещений.
    
    - total_visits: общее количество
    - unique_clients: уникальные клиенты
    - avg_duration_minutes: средняя длительность
    - peak_hours: распределение по часам
    - visits_by_day: распределение по дням
    - visits_by_zone: распределение по зонам
    """
    service = VisitService(db)
    return service.get_stats(
        period=period,
        start_date=start_date,
        end_date=end_date,
        zone=zone,
    )


@router.get(
    "/stats/today",
    response_model=VisitStatsResponse,
    status_code=status.HTTP_200_OK,
)
def get_today_stats(
    zone: str | None = Query(default=None, description="Фильтр по зоне"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Получить статистику за сегодня"""
    service = VisitService(db)
    today = date.today()
    return service.get_stats(
        period="day",
        start_date=today,
        end_date=today,
        zone=zone,
    )


@router.get(
    "/stats/week",
    response_model=VisitStatsResponse,
    status_code=status.HTTP_200_OK,
)
def get_week_stats(
    start_date: date = Query(description="Начало недели"),
    zone: str | None = Query(default=None, description="Фильтр по зоне"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Получить статистику за неделю"""
    service = VisitService(db)
    return service.get_stats(
        period="week",
        start_date=start_date,
        zone=zone,
    )


@router.get(
    "/stats/month",
    response_model=VisitStatsResponse,
    status_code=status.HTTP_200_OK,
)
def get_month_stats(
    start_date: date = Query(description="Начало месяца"),
    zone: str | None = Query(default=None, description="Фильтр по зоне"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Получить статистику за месяц"""
    service = VisitService(db)
    return service.get_stats(
        period="month",
        start_date=start_date,
        zone=zone,
    )