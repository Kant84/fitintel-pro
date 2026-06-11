# app/api/v1/gamification.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission, get_current_user
from app.db.session import get_db
from app.services.gamification_service import GamificationService

router = APIRouter(prefix="/gamification", tags=["Gamification"])


def get_service(db: Session = Depends(get_db)) -> GamificationService:
    return GamificationService(db)


@router.get("/levels")
def list_levels(
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_permission("gamification.read")),
    service: GamificationService = Depends(get_service),
):
    """Топ клиентов (лидерборд)"""
    return {"leaderboard": service.get_leaderboard(limit)}


@router.get("/my")
def my_progress(
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """Мой прогресс XP, уровень, достижения"""
    return service.get_client_progress(current_user.id)


@router.get("/clients/{client_id}")
def client_progress(
    client_id: UUID,
    current_user=Depends(require_permission("gamification.read")),
    service: GamificationService = Depends(get_service),
):
    """Прогресс конкретного клиента"""
    return service.get_client_progress(client_id)
