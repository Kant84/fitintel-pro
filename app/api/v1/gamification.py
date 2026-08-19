# app/api/v1/gamification.py
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission, get_current_user
from app.db.session import get_db
from app.services.gamification_service import GamificationService

router = APIRouter(prefix="/gamification", tags=["Gamification"])


def get_service(db: Session = Depends(get_db)) -> GamificationService:
    return GamificationService(db)


# ---------- схемы ----------

class AwardXPRequest(BaseModel):
    client_id: UUID
    amount: int
    reason: str = "manual"


class VisitRequest(BaseModel):
    client_id: UUID
    entry_at: datetime
    exit_at: Optional[datetime] = None
    workout_minutes: int = 0


class RewardActivateRequest(BaseModel):
    client_id: UUID


class AchievementDefCreate(BaseModel):
    name: str
    condition_type: str  # visits_count | streak_days | workout_minutes
    condition_value: int
    xp_reward: int = 0


class XPRulesUpdate(BaseModel):
    rules: dict


# ---------- чтение ----------

@router.get("/levels")
def list_levels(
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """Топ клиентов (лидерборд)"""
    return {"leaderboard": service.get_leaderboard(limit=limit)}


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
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """Прогресс конкретного клиента"""
    return service.get_client_progress(client_id)


# ---------- E21.1 начисление XP ----------

@router.post("/award-xp")
def award_xp(
    data: AwardXPRequest,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.1: начислить XP клиенту"""
    return service.award_xp(data.client_id, data.amount, data.reason)


# ---------- E21.2 уровень клиента ----------

@router.get("/level")
def client_level(
    client_id: UUID,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.2: уровень и прогресс клиента"""
    return service.get_client_progress(client_id)


# ---------- E21.3 достижения клиента ----------

@router.get("/achievements")
def client_achievements(
    client_id: UUID,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.3: разблокированные достижения клиента"""
    return {"achievements": service._get_achievements(client_id)}


# ---------- E21.14 прогресс по достижениям ----------

@router.get("/achievements/progress")
def achievement_progress(
    client_id: UUID,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.14: прогресс до достижений (проценты, остаток)"""
    return {"progress": service.get_achievement_progress(client_id)}


# ---------- E21.8 создание достижения (админ) ----------

@router.post("/achievements", status_code=201)
def create_achievement_def(
    data: AchievementDefCreate,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.8: создать определение достижения"""
    d = service.create_achievement_def(
        data.name, data.condition_type, data.condition_value, data.xp_reward
    )
    return {
        "achievement_id": str(d.id),
        "name": d.name,
        "condition_type": d.condition_type,
        "condition_value": d.condition_value,
        "xp_reward": d.xp_reward,
    }


# ---------- E21.4 лидерборд ----------

@router.get("/leaderboard")
def leaderboard(
    period: str = Query(default="all", regex="^(week|month|all)$"),
    limit: int = Query(default=10, ge=1, le=100),
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.4: топ клиентов по XP"""
    return {"period": period, "leaderboard": service.get_leaderboard(period=period, limit=limit)}


# ---------- E21.5-7 награды ----------

@router.get("/rewards")
def list_rewards(
    client_id: UUID,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.5: награды, доступные клиенту"""
    return {"rewards": service.get_rewards(client_id)}


@router.post("/rewards/{reward_id}/activate")
def activate_reward(
    reward_id: UUID,
    data: RewardActivateRequest,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.6/21.7: активировать награду (повторно — 400)"""
    result = service.activate_reward(data.client_id, reward_id)
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ---------- E21.9 правила XP ----------

@router.get("/xp-rules")
def get_xp_rules(
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    return service.get_xp_rules()


@router.put("/xp-rules")
def update_xp_rules(
    data: XPRulesUpdate,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.9: обновить множители XP"""
    return service.update_xp_rules(data.rules)


# ---------- E21.10-13 обработка визита (streak, авто-достижения) ----------

@router.post("/visit")
def process_visit(
    data: VisitRequest,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.10-13: обработать посещение (XP, streak, авто-достижения)"""
    return service.process_visit(
        data.client_id, data.entry_at, data.exit_at, data.workout_minutes
    )


# ---------- E21.15 сводка для мобильного приложения ----------

@router.get("/mobile/summary")
def mobile_summary(
    client_id: UUID,
    current_user=Depends(get_current_user),
    service: GamificationService = Depends(get_service),
):
    """E21.15: сводка геймификации для мобильного приложения"""
    return service.get_mobile_summary(client_id)
