# app/api/v1/visits.py

from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from datetime import datetime
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



# список всех визитов (GET /)
@router.get(
    "/",
    response_model=VisitListResponse,
)
def list_visits(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission('visits.read')),
    db: Session = Depends(get_db),
):
    """Получить список всех визитов"""
    service = VisitService(db)
    visits = service.list_all(limit=limit, offset=offset)
    return VisitListResponse(items=visits, count=len(visits))

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
    # DEBUG
    print(f"DEBUG payload type: {type(payload)}")
    print(f"DEBUG payload dict: {payload.model_dump()}")
    print(f"DEBUG face_id repr: {repr(payload.face_id)}")
    print(f"DEBUG face_id is None: {payload.face_id is None}")
    print(f"DEBUG face_id == '': {payload.face_id == ''}")
    
    # Проверяем, что указан хотя бы один идентификатор
    has_id = any([
        payload.client_id,
        payload.card_id,
        payload.face_id,
        payload.qr_payload,
    ])
    print(f"DEBUG has_id={has_id}")
    if not has_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать client_id, card_id, face_id или qr_payload",
        )
    
    service = VisitService(db)
    visit = service.entry(
        client_id=str(payload.client_id) if payload.client_id else None,
        subscription_id=str(payload.subscription_id) if payload.subscription_id else None,
        access_method=payload.access_method,
        access_device_id=payload.access_device_id,
        zone=payload.zone,
        entry_time=payload.entry_time,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
        card_id=payload.card_id,
        face_id=payload.face_id,
        qr_payload=payload.qr_payload,
        face_confidence=payload.face_confidence,
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
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(visit)


# ==========================================================
# АЛИАСЫ ДЛЯ ТЕСТОВЫХ КЕЙСОВ (E8)
# ==========================================================
@router.post(
    "/check-in",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
)
def check_in(
    payload: VisitEntryRequest,
    current_user=Depends(require_permission("visits.create")),
    db: Session = Depends(get_db),
):
    """
    Алиас для /entry — регистрация входа клиента.
    """
    print(f"DEBUG check_in STARTED: {payload.model_dump()}")
    service = VisitService(db)
    visit = service.entry(
        client_id=str(payload.client_id) if payload.client_id else None,
        subscription_id=str(payload.subscription_id) if payload.subscription_id else None,
        access_method=payload.access_method,
        access_device_id=payload.access_device_id,
        zone=payload.zone,
        entry_time=payload.entry_time,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
        card_id=payload.card_id,
        face_id=payload.face_id,
        qr_payload=payload.qr_payload,
        face_confidence=payload.face_confidence,
    )
    return service._build_response(visit)


@router.post(
    "/check-out",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def check_out(
    payload: VisitExitRequest,
    current_user=Depends(require_permission("visits.update")),
    db: Session = Depends(get_db),
):
    """
    Алиас для /exit — регистрация выхода клиента.
    """
    service = VisitService(db)
    visit = service.exit(
        visit_id=str(payload.visit_id),
        exit_time=payload.exit_time,
        notes=payload.notes,
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
        notes=payload.notes,
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

# ============================================================
# Статистика посещений
# ============================================================
@router.get("/stats", response_model=dict)
def get_visit_stats(
    date_from: str | None = Query(default=None, description="Дата начала периода (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Дата конца периода (YYYY-MM-DD)"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Статистика посещений с выбором периода"""
    from datetime import datetime, date
    visit_service = VisitService(db)
    
    # Получаем все посещения
    visits = visit_service.list_all(limit=10000, offset=0)
    
    # Фильтруем по периоду
    if date_from:
        from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        visits = [v for v in visits if v.entry_time and v.entry_time.date() >= from_date]
    
    if date_to:
        to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        visits = [v for v in visits if v.entry_time and v.entry_time.date() <= to_date]
    
    # Считаем статистику
    total = len(visits)
    active = sum(1 for v in visits if v.status == "ACTIVE")
    completed = sum(1 for v in visits if v.status == "COMPLETED")
    denied = sum(1 for v in visits if v.access_granted == False)
    
    return {
        "total_visits": total,
        "active_visits": active,
        "completed_visits": completed,
        "denied_visits": denied,
        "period": {
            "date_from": date_from,
            "date_to": date_to,
        },
    }


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





# ==========================================================
# АВТО-ЗАКРЫТИЕ ПОСЕЩЕНИЙ (E8.11)
# ==========================================================
@router.post(
    "/auto-close",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def auto_close_visits(
    days_threshold: int = Query(default=1, ge=1, le=30, description="Закрыть посещения старше N дней"),
    current_user=Depends(require_permission("visits.update")),
    db: Session = Depends(get_db),
):
    """
    Авто-закрытие незавершённых посещений.
    
    Закрывает посещения, где клиент вошёл, но не вышел,
    и прошло более N дней.
    """
    service = VisitService(db)
    closed_count = service.close_incomplete_visits(days_threshold=days_threshold)
    return {
        "closed_count": closed_count,
        "message": f"Закрыто {closed_count} незавершённых посещений",
    }
