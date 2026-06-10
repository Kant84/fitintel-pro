# app/api/v1/online_training.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/online-training", tags=["Online Training"])


@router.get("/sessions")
def list_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Спис онлайн-тренировок"""
    return {"items": []}


@router.post("/sessions")
def create_session(
    payload: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создать онлайн-тренировку"""
    import uuid
    from app.db.base import utc_now
    return {"id": str(uuid.uuid4()), "status": "scheduled", "created_at": utc_now().isoformat()}


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить тренировку"""
    return {"id": session_id, "status": "live", "participants": 0}
