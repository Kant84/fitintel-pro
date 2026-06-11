# app/api/v1/online_training.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission, get_current_user
from app.db.session import get_db
from app.services.online_training_service import OnlineTrainingService

router = APIRouter(prefix="/online-training", tags=["Online Training"])


def get_service(db: Session = Depends(get_db)) -> OnlineTrainingService:
    return OnlineTrainingService(db)


# ============================================================
# ПУБЛИЧНЫЕ (для клиентов)
# ============================================================

@router.get("/catalog")
def training_catalog(
    service: OnlineTrainingService = Depends(get_service),
):
    """Каталог тренировок по категориям"""
    return service.get_catalog()


@router.get("/live-now")
def live_now(
    service: OnlineTrainingService = Depends(get_service),
):
    """Текущие live-трансляции"""
    return {"sessions": service.get_live_now()}


@router.get("/upcoming")
def upcoming_sessions(
    service: OnlineTrainingService = Depends(get_service),
):
    """Ближайшие запланированные"""
    return {"sessions": service.get_upcoming()}


# ============================================================
# CRUD
# ============================================================

@router.get("/sessions")
def list_sessions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    category: str | None = None,
    difficulty: str | None = None,
    session_type: str | None = None,
    current_user=Depends(require_permission("online_training.read")),
    service: OnlineTrainingService = Depends(get_service),
):
    """Список сессий"""
    return service.list_sessions(offset, limit, category, difficulty, session_type)


@router.post("/sessions")
def create_session(
    payload: dict,
    current_user=Depends(require_permission("online_training.create")),
    service: OnlineTrainingService = Depends(get_service),
):
    """Создать сессию"""
    return service.create_session(payload, trainer_id=current_user.id)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: UUID,
    current_user=Depends(require_permission("online_training.read")),
    service: OnlineTrainingService = Depends(get_service),
):
    """Получить сессию"""
    return service._serialize_session(service.get_session(session_id))


@router.patch("/sessions/{session_id}")
def update_session(
    session_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("online_training.update")),
    service: OnlineTrainingService = Depends(get_service),
):
    """Обновить сессию"""
    return service.update_session(session_id, payload)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: UUID,
    current_user=Depends(require_permission("online_training.delete")),
    service: OnlineTrainingService = Depends(get_service),
):
    """Удалить сессию"""
    service.delete_session(session_id)
    return {"status": "deleted"}


# ============================================================
# УЧАСТНИКИ
# ============================================================

@router.post("/sessions/{session_id}/register")
def register_participant(
    session_id: UUID,
    current_user=Depends(get_current_user),
    service: OnlineTrainingService = Depends(get_service),
):
    """Зарегистрироваться на сессию"""
    return service.register_participant(session_id, current_user.id)


@router.post("/sessions/{session_id}/join")
def join_session(
    session_id: UUID,
    current_user=Depends(get_current_user),
    service: OnlineTrainingService = Depends(get_service),
):
    """Присоединиться к live-сессии"""
    return service.join_session(session_id, current_user.id)


@router.post("/sessions/{session_id}/leave")
def leave_session(
    session_id: UUID,
    current_user=Depends(get_current_user),
    service: OnlineTrainingService = Depends(get_service),
):
    """Покинуть сессию"""
    return service.leave_session(session_id, current_user.id)


@router.post("/sessions/{session_id}/rate")
def rate_session(
    session_id: UUID,
    payload: dict,
    current_user=Depends(get_current_user),
    service: OnlineTrainingService = Depends(get_service),
):
    """Оценить сессию"""
    return service.rate_session(
        session_id, current_user.id,
        rating=payload.get("rating", 5),
        feedback=payload.get("feedback"),
    )


@router.get("/sessions/{session_id}/participants")
def session_participants(
    session_id: UUID,
    current_user=Depends(require_permission("online_training.read")),
    service: OnlineTrainingService = Depends(get_service),
):
    """Участники сессии"""
    return {"participants": service.get_participants(session_id)}


# ============================================================
# СТАТИСТИКА
# ============================================================

@router.get("/stats")
def training_stats(
    current_user=Depends(require_permission("online_training.read")),
    service: OnlineTrainingService = Depends(get_service),
):
    """Статистика онлайн-тренировок"""
    return service.get_stats()
