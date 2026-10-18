from typing import Optional
# app/api/v1/visits.py

from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    # FIX: нормализация статусов для Pydantic enum
    for _v in visits:
        if hasattr(_v, "status") and _v.status:
            _v.status = _v.status.upper()
        if hasattr(_v, "access_method") and _v.access_method:
            _v.access_method = _v.access_method.upper()
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
    
    # Проверяем, что указан хотя бы один идентификатор
    has_id = any([
        payload.client_id,
        payload.card_id,
        payload.face_id,
        payload.qr_payload,
    ])
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
        
        actor_user_id=str(current_user.id),
        card_id=payload.card_id,
        face_id=payload.face_id,
        qr_payload=payload.qr_payload,
        face_confidence=payload.face_confidence,
    )
        # E60: трекинг для ML. ВАЖНО: при ошибке логгера откатываем транзакцию,
        # иначе aborted-транзакция уронит сборку ответа (500 после создания визита).
    try:
        from app.ml.event_logger import EventLogger
        EventLogger(db).log("visit_entry", {
            "client_id": str(payload.client_id) if payload.client_id else None,
            "access_method": payload.access_method,
            "zone": payload.zone,
        }, user_id=str(current_user.id), source="skud")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[WARN] EventLogger visit_entry failed (ignored): {e}")
    # W6: бонусы за посещение (правила «Бонусы», защита от дублей)
    try:
        from sqlalchemy import text as _txt
        from app.api.v1.miniapp_config import award_bonus
        from app.api.v1.club_params import get_param
        _cid = str(payload.client_id) if getattr(payload, "client_id", None) else None
        if _cid:
            _cd = float(get_param("BONUS_VISIT_COOLDOWN_HOURS", "12") or 12)
            _et = getattr(visit, "entry_time", None)
            if _et is not None:
                _prev = db.execute(_txt("SELECT max(entry_time) FROM visits "
                                        "WHERE client_id::text=:c AND entry_time < :t"),
                                   {"c": _cid, "t": _et}).scalar()
                _ok = _prev is None or (_et.replace(tzinfo=None) - _prev.replace(tzinfo=None)).total_seconds() >= _cd * 3600
                if _ok:
                    _bonus = award_bonus(db, _cid, "visit")
                    if _bonus and _bonus > 0:
                        _row = db.execute(_txt("SELECT phone FROM clients WHERE id::text=:c"), {"c": _cid}).first()
                        if _row and _row[0]:
                            from app.integrations.max.service import get_max_service
                            get_max_service().send_message(phone_number=str(_row[0]),
                                text=("🎁 +%d бонусов за посещение! Приходите чаще 💪" % int(_bonus)))
    except Exception as _e:
        db.rollback()
        print(f"[WARN] bonus visit award failed (ignored): {_e}")
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
        # E60: трекинг для ML. ВАЖНО: при ошибке логгера откатываем транзакцию,
        # иначе aborted-транзакция уронит сборку ответа (500 после создания визита).
    try:
        from app.ml.event_logger import EventLogger
        EventLogger(db).log("visit_entry", {
            "client_id": str(payload.client_id),
            "access_method": payload.access_method.value if hasattr(payload.access_method, "value") else str(payload.access_method),
            "zone": payload.zone,
            "manual": True,
        }, user_id=str(current_user.id), source="reception")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[WARN] EventLogger visit_entry failed (ignored): {e}")
    # W6: бонусы за посещение (правила «Бонусы», защита от дублей)
    try:
        from sqlalchemy import text as _txt
        from app.api.v1.miniapp_config import award_bonus
        from app.api.v1.club_params import get_param
        _cid = str(payload.client_id) if getattr(payload, "client_id", None) else None
        if _cid:
            _cd = float(get_param("BONUS_VISIT_COOLDOWN_HOURS", "12") or 12)
            _et = getattr(visit, "entry_time", None)
            if _et is not None:
                _prev = db.execute(_txt("SELECT max(entry_time) FROM visits "
                                        "WHERE client_id::text=:c AND entry_time < :t"),
                                   {"c": _cid, "t": _et}).scalar()
                _ok = _prev is None or (_et.replace(tzinfo=None) - _prev.replace(tzinfo=None)).total_seconds() >= _cd * 3600
                if _ok:
                    _bonus = award_bonus(db, _cid, "visit")
                    if _bonus and _bonus > 0:
                        _row = db.execute(_txt("SELECT phone FROM clients WHERE id::text=:c"), {"c": _cid}).first()
                        if _row and _row[0]:
                            from app.integrations.max.service import get_max_service
                            get_max_service().send_message(phone_number=str(_row[0]),
                                text=("🎁 +%d бонусов за посещение! Приходите чаще 💪" % int(_bonus)))
    except Exception as _e:
        db.rollback()
        print(f"[WARN] bonus visit award failed (ignored): {_e}")
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

    from datetime import date as _dte, timedelta as _tdl
    _today = _dte.today()
    _week = _today - _tdl(days=_today.weekday())
    _month = _today.replace(day=1)

    def _vd(v):
        try:
            return v.entry_time.date() if v.entry_time else None
        except Exception:
            return None
    
    return {
        "today": sum(1 for v in visits if _vd(v) == _today),
        "week": sum(1 for v in visits if _vd(v) and _vd(v) >= _week),
        "month": sum(1 for v in visits if _vd(v) and _vd(v) >= _month),
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



# ==========================================================
# СТАТИСТИКА
# ==========================================================

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

# ============================================================
# Динамика посещений (тренд)
# ============================================================
@router.get("/stats/trend")
def visits_stats_trend(
    granularity: str = Query("week", pattern="^(day|week|month)$"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    from sqlalchemy import text as _text
    trunc = {"day": "day", "week": "week", "month": "month"}[granularity]
    sql = ("SELECT date_trunc('" + trunc + "', entry_time)::date AS date, count(*) AS count "
           "FROM visits WHERE entry_time IS NOT NULL")
    params = {}
    if from_:
        sql += " AND entry_time::date >= :f"; params["f"] = from_
    if to:
        sql += " AND entry_time::date <= :t"; params["t"] = to
    sql += " GROUP BY 1 ORDER BY 1"
    rows = db.execute(_text(sql), params).mappings().all()
    return [{"date": str(r["date"]), "count": int(r["count"])} for r in rows]