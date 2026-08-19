"""GamificationService — XP, уровни, достижения, streak, награды, правила XP."""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.models.gamification_level import (
    GamificationLevel, Achievement, AchievementDef,
    Reward, RewardActivation, XPRule,
    xp_needed_for_next, MAX_LEVEL,
)
from app.models.client import Client

XP_PER_VISIT = 10
XP_PER_MINUTE = 0.1
STREAK_BONUS_XP = 5

ACHIEVEMENT_DEFS = {
    "first_visit": {"title": "Первый шаг", "description": "Первое посещение клуба", "xp_reward": 50, "icon": "target"},
    "week_warrior": {"title": "Воин недели", "description": "7 посещений", "xp_reward": 200, "icon": "sword"},
    "month_master": {"title": "Мастер месяца", "description": "20 посещений", "xp_reward": 500, "icon": "crown"},
    "centurion": {"title": "Центурион", "description": "100 посещений", "xp_reward": 100, "icon": "hundred"},
    "early_bird": {"title": "Ранняя пташка", "description": "Тренировка до 8 утра", "xp_reward": 150, "icon": "sunrise"},
    "night_owl": {"title": "Ночная сова", "description": "Тренировка после 22:00", "xp_reward": 300, "icon": "owl"},
    "marathon": {"title": "Марафонец", "description": "Тренировка дольше 2 часов", "xp_reward": 300, "icon": "runner"},
    "streak_7": {"title": "Неделя огня", "description": "7 дней посещений без пропусков", "xp_reward": 350, "icon": "fire"},
}


class GamificationService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- базовое ----------

    def get_or_create_level(self, client_id: UUID) -> GamificationLevel:
        level = self.db.query(GamificationLevel).filter(
            GamificationLevel.client_id == client_id
        ).first()
        if not level:
            level = GamificationLevel(
                client_id=client_id, level=1, current_xp=0,
                xp_to_next=xp_needed_for_next(1),
                total_visits=0, total_workout_minutes=0,
                streak_days=0, max_streak_days=0, last_visit_date=None,
                achievements_count=0,
            )
            self.db.add(level)
            self.db.commit()
            self.db.refresh(level)
        return level

    def _client_name(self, client) -> str:
        for attr in ("full_name", "name"):
            v = getattr(client, attr, None)
            if v:
                return v
        fn = getattr(client, "first_name", "") or ""
        ln = getattr(client, "last_name", "") or ""
        return (fn + " " + ln).strip() or str(client.id)

    def _get_level_title(self, level: int) -> str:
        if level >= 50:
            return "Легенда клуба"
        if level >= 30:
            return "Мастер"
        if level >= 20:
            return "Эксперт"
        if level >= 10:
            return "Профи"
        if level >= 5:
            return "Любитель"
        return "Новичок"

    def _get_client_rank(self, current_xp: int) -> int:
        higher = self.db.query(GamificationLevel).filter(
            GamificationLevel.current_xp > current_xp
        ).count()
        return higher + 1

    def _get_achievements(self, client_id: UUID) -> list:
        rows = self.db.query(Achievement).filter(
            Achievement.client_id == client_id
        ).order_by(desc(Achievement.created_at)).all()
        return [{
            "id": str(a.id), "type": a.achievement_type, "title": a.title,
            "description": a.description, "xp_reward": a.xp_reward,
            "icon": a.icon,
            "unlocked_at": a.created_at.isoformat() if a.created_at else None,
        } for a in rows]

    def _get_next_rewards(self, level: int) -> list:
        rows = self.db.query(Reward).filter(
            Reward.is_active == True, Reward.level_required > level
        ).order_by(Reward.level_required).limit(3).all()
        return [{"title": r.title, "required_level": r.level_required} for r in rows]

    def get_client_progress(self, client_id: UUID) -> dict:
        level = self.get_or_create_level(client_id)
        progress = round(level.current_xp / level.xp_to_next * 100, 1) if level.xp_to_next else 100.0
        return {
            "client_id": str(client_id),
            "current_level": level.level,
            "level_title": self._get_level_title(level.level),
            "current_xp": level.current_xp,
            "xp_to_next": level.xp_to_next,
            "progress_percent": progress,
            "rank": self._get_client_rank(level.current_xp),
            "streak_days": level.streak_days,
            "max_streak_days": level.max_streak_days,
            "total_visits": level.total_visits,
            "total_workout_minutes": level.total_workout_minutes,
            "achievements_count": self.db.query(Achievement).filter(
                Achievement.client_id == client_id
            ).count(),
            "achievements": self._get_achievements(client_id),
            "next_rewards": self._get_next_rewards(level.level),
        }

    def get_leaderboard(self, period: Optional[str] = None, limit: int = 10) -> list:
        # period: week | month | all — пока учитываем общий XP (period принимаем для совместимости)
        rows = (
            self.db.query(GamificationLevel, Client)
            .join(Client, GamificationLevel.client_id == Client.id)
            .order_by(desc(GamificationLevel.current_xp))
            .limit(limit).all()
        )
        return [{
            "rank": i + 1,
            "client_id": str(level.client_id),
            "client_name": self._client_name(client),
            "current_xp": level.current_xp,
            "level": level.level,
            "level_title": self._get_level_title(level.level),
            "streak_days": level.streak_days,
        } for i, (level, client) in enumerate(rows)]

    # ---------- XP ----------

    def _add_xp(self, level: GamificationLevel, amount: int) -> bool:
        level.current_xp += amount
        leveled_up = False
        while level.level < MAX_LEVEL and level.current_xp >= level.xp_to_next:
            level.current_xp -= level.xp_to_next
            level.level += 1
            level.xp_to_next = xp_needed_for_next(level.level)
            leveled_up = True
        return leveled_up

    def award_xp(self, client_id: UUID, amount: int, reason: str = "manual") -> dict:
        level = self.get_or_create_level(client_id)
        leveled_up = self._add_xp(level, int(amount))
        self.db.commit()
        self.db.refresh(level)
        return {
            "client_id": str(client_id),
            "xp_awarded": int(amount),
            "reason": reason,
            "current_xp": level.current_xp,
            "level": level.level,
            "level_title": self._get_level_title(level.level),
            "leveled_up": leveled_up,
            "new_level": level.level if leveled_up else None,
        }

    # ---------- визиты и streak ----------

    def _rules(self) -> dict:
        rules = {r.key: r.value for r in self.db.query(XPRule).all()}
        return {
            "xp_per_visit": rules.get("xp_per_visit", XP_PER_VISIT),
            "xp_per_minute": rules.get("xp_per_minute", XP_PER_MINUTE),
            "streak_bonus_xp": rules.get("streak_bonus_xp", STREAK_BONUS_XP),
        }

    def _update_streak(self, level: GamificationLevel, entry_at: datetime) -> int:
        today = entry_at.date()
        if level.last_visit_date == today:
            return 0
        if level.last_visit_date is not None and level.last_visit_date == today - timedelta(days=1):
            level.streak_days += 1
        else:
            level.streak_days = 1
        level.max_streak_days = max(level.max_streak_days, level.streak_days)
        level.last_visit_date = today
        if level.streak_days > 1:
            return self._rules()["streak_bonus_xp"] * level.streak_days
        return 0

    def process_visit(self, client_id: UUID, entry_at: datetime,
                      exit_at: Optional[datetime] = None, workout_minutes: int = 0) -> dict:
        level = self.get_or_create_level(client_id)
        rules = self._rules()
        xp_earned = int(rules["xp_per_visit"] + workout_minutes * rules["xp_per_minute"])
        streak_bonus = self._update_streak(level, entry_at)
        xp_earned += streak_bonus
        leveled_up = self._add_xp(level, xp_earned)
        level.total_visits += 1
        level.total_workout_minutes += workout_minutes
        new_achievements = self._check_achievements(client_id, level, entry_at, exit_at)
        level.achievements_count = self.db.query(Achievement).filter(
            Achievement.client_id == client_id
        ).count()
        self.db.commit()
        return {
            "xp_earned": xp_earned,
            "streak_bonus": streak_bonus,
            "leveled_up": leveled_up,
            "level": level.level,
            "streak_days": level.streak_days,
            "total_visits": level.total_visits,
            "new_achievements": new_achievements,
        }

    def _check_achievements(self, client_id: UUID, level: GamificationLevel,
                            entry_at: Optional[datetime] = None,
                            exit_at: Optional[datetime] = None) -> list:
        existing = {a.achievement_type for a in self.db.query(Achievement).filter(
            Achievement.client_id == client_id
        ).all()}
        checks = {
            "first_visit": level.total_visits >= 1,
            "week_warrior": level.total_visits >= 7,
            "month_master": level.total_visits >= 20,
            "centurion": level.total_visits >= 100,
            "streak_7": level.streak_days >= 7,
        }
        if entry_at is not None:
            checks["early_bird"] = entry_at.hour < 8
            checks["night_owl"] = entry_at.hour >= 22
        if entry_at is not None and exit_at is not None:
            checks["marathon"] = (exit_at - entry_at).total_seconds() >= 2 * 3600

        new = []
        for key, cond in checks.items():
            if cond and key not in existing:
                d = ACHIEVEMENT_DEFS[key]
                ach = Achievement(
                    client_id=client_id, achievement_type=key,
                    title=d["title"], description=d["description"],
                    xp_reward=d["xp_reward"], icon=d["icon"],
                )
                self.db.add(ach)
                self._add_xp(level, d["xp_reward"])
                new.append({"type": key, "title": d["title"], "xp_reward": d["xp_reward"]})

        # кастомные условия из achievement_defs (E21.8)
        metrics = {
            "visits_count": level.total_visits,
            "streak_days": level.streak_days,
            "workout_minutes": level.total_workout_minutes,
        }
        for d in self.db.query(AchievementDef).all():
            key = f"def_{d.id}"
            if key in existing:
                continue
            if metrics.get(d.condition_type, 0) >= d.condition_value:
                ach = Achievement(
                    client_id=client_id, achievement_type=key,
                    title=d.name, description=f"Условие: {d.condition_type} >= {d.condition_value}",
                    xp_reward=d.xp_reward, icon=d.icon,
                )
                self.db.add(ach)
                self._add_xp(level, d.xp_reward)
                new.append({"type": key, "title": d.name, "xp_reward": d.xp_reward})
        return new

    # ---------- достижения: прогресс (E21.14) ----------

    def get_achievement_progress(self, client_id: UUID) -> list:
        level = self.get_or_create_level(client_id)
        unlocked = {a.achievement_type for a in self.db.query(Achievement).filter(
            Achievement.client_id == client_id
        ).all()}
        metrics = {
            "visits_count": level.total_visits,
            "streak_days": level.streak_days,
            "workout_minutes": level.total_workout_minutes,
        }
        out = []
        for d in self.db.query(AchievementDef).all():
            cur = metrics.get(d.condition_type, 0)
            pct = min(100.0, round(cur / d.condition_value * 100, 1)) if d.condition_value else 100.0
            out.append({
                "id": str(d.id),
                "name": d.name,
                "condition_type": d.condition_type,
                "condition_value": d.condition_value,
                "current_value": cur,
                "progress_percent": pct,
                "remaining": max(0, d.condition_value - cur),
                "unlocked": f"def_{d.id}" in unlocked,
            })
        return out

    # ---------- награды ----------

    def get_rewards(self, client_id: UUID) -> list:
        level = self.get_or_create_level(client_id)
        used_ids = {a.reward_id for a in self.db.query(RewardActivation).filter(
            RewardActivation.client_id == client_id
        ).all()}
        out = []
        for r in self.db.query(Reward).filter(Reward.is_active == True).order_by(Reward.level_required).all():
            out.append({
                "id": str(r.id),
                "title": r.title,
                "description": r.description,
                "level_required": r.level_required,
                "discount_percent": r.discount_percent,
                "available": level.level >= r.level_required,
                "used": r.id in used_ids,
            })
        return out

    def activate_reward(self, client_id: UUID, reward_id: UUID) -> dict:
        level = self.get_or_create_level(client_id)
        reward = self.db.query(Reward).filter(Reward.id == reward_id).first()
        if not reward or not reward.is_active:
            return {"error": "not_found", "message": "Награда не найдена"}
        existing = self.db.query(RewardActivation).filter(
            RewardActivation.reward_id == reward_id,
            RewardActivation.client_id == client_id,
        ).first()
        if existing:
            return {"error": "already_used", "message": "Награда уже использована"}
        if level.level < reward.level_required:
            return {"error": "level_too_low",
                    "message": f"Награда доступна с уровня {reward.level_required}"}
        act = RewardActivation(reward_id=reward_id, client_id=client_id, is_used=True)
        self.db.add(act)
        self.db.commit()
        return {
            "success": True,
            "reward_id": str(reward.id),
            "title": reward.title,
            "discount_percent": reward.discount_percent,
            "activated_at": act.created_at.isoformat() if act.created_at else None,
        }

    # ---------- админ: достижения и правила ----------

    def create_achievement_def(self, name: str, condition_type: str,
                               condition_value: int, xp_reward: int = 0) -> AchievementDef:
        d = AchievementDef(name=name, condition_type=condition_type,
                           condition_value=condition_value, xp_reward=xp_reward)
        self.db.add(d)
        self.db.commit()
        self.db.refresh(d)
        return d

    def get_xp_rules(self) -> dict:
        rules = {r.key: r.value for r in self.db.query(XPRule).all()}
        return {
            "xp_per_visit": rules.get("xp_per_visit", XP_PER_VISIT),
            "xp_per_minute": rules.get("xp_per_minute", XP_PER_MINUTE),
            "streak_bonus_xp": rules.get("streak_bonus_xp", STREAK_BONUS_XP),
            **rules,
        }

    def update_xp_rules(self, rules: dict) -> dict:
        for k, v in rules.items():
            rule = self.db.query(XPRule).filter(XPRule.key == k).first()
            if rule:
                rule.value = int(v)
            else:
                self.db.add(XPRule(key=k, value=int(v)))
        self.db.commit()
        return self.get_xp_rules()

    # ---------- мобильное приложение (E21.15) ----------

    def get_mobile_summary(self, client_id: UUID) -> dict:
        progress = self.get_client_progress(client_id)
        rewards = [r for r in self.get_rewards(client_id) if not r["used"]][:3]
        return {
            "client_id": str(client_id),
            "level": progress["current_level"],
            "level_title": progress["level_title"],
            "current_xp": progress["current_xp"],
            "xp_to_next": progress["xp_to_next"],
            "progress_percent": progress["progress_percent"],
            "streak_days": progress["streak_days"],
            "achievements_count": progress["achievements_count"],
            "rank": progress["rank"],
            "next_rewards": rewards,
        }
