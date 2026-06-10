# app/api/v1/gamification.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/gamification", tags=["Gamification"])


@router.get("/levels")
def levels(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Уровни геймификации"""
    return {"levels": [
        {"id": 1, "name": "Новичок", "min_visits": 0, "color": "#CD7F32"},
        {"id": 2, "name": "Бронза", "min_visits": 10, "color": "#B87333"},
        {"id": 3, "name": "Серебро", "min_visits": 30, "color": "#C0C0C0"},
        {"id": 4, "name": "Золото", "min_visits": 60, "color": "#FFD700"},
        {"id": 5, "name": "Платина", "min_visits": 100, "color": "#E5E4E2"},
    ]}


@router.get("/my")
def my_gamification(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Мой прогресс геймификации"""
    return {
        "user_id": str(current_user.id),
        "current_level": {"id": 1, "name": "Новичок"},
        "visits_total": 0,
        "visits_to_next": 10,
        "achievements": [],
        "points": 0,
    }
