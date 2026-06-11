# app/services/gamification_service.py

from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from app.models.client import Client
from app.models.gamification_level import (
    GamificationLevel, Achievement, xp_for_level, xp_needed_for_next, MAX_LEVEL
)
from app.models.visit import Visit


# Таблица достижений
ACHIEVEMENT_DEFS = {
    "first_visit": {"title": "Первый шаг", "description": "Первое посещение клуба", "xp": 50, "icon": "🎯"},
    "week_warrior": {"title": "Недельный воин", "description": "7 дней посещений подряд", "xp": 200, "icon": "🔥"},
    "month_master": {"title": "Месячный мастер", "description": "30 дней посещений подряд", "xp": 500, "icon": "👑"},
    "centurion": {"title": "Центурион", "description": "100 посещений", "xp": 1000, "icon": "💯"},
    "early_bird": {"title": "Ранняя пташка", "description": "10 утренних тренировок (до 9:00)", "xp": 150, "icon": "🌅"},
    "night_owl": {"title": "Сова", "description": "10 вечерних тренировок (после 20:00)", "xp": 150, "icon": "🌙"},
    " marathon": {"title": "Марафонец", "description": "500 минут тренировок", "xp": 300, "icon": "🏃"},
    "loyal": {"title": "Преданный", "description": "1 год в клубе", "xp": 2000, "icon": "⭐"},
}

XP_PER_VISIT = 10
XP_PER_MINUTE = 0.1  # XP за минуту тренировки
STREAK_BONUS_XP = 5  # Бонус за каждый день streak


class GamificationService:
    """Сервис геймификации: XP, уровни, достижения, серии"""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================
    # ПОЛУЧЕНИЕ / СОЗДАНИЕ
    # ============================================================

    def get_or_create_level(self, client_id: UUID) -> GamificationLevel:
        """Получить или создать прогресс клиента"""
        level = self.db.execute(
            select(GamificationLevel).where(GamificationLevel.client_id == str(client_id))
        ).scalar_one_or_none()

        if not level:
            level = GamificationLevel(
                client_id=str(client_id),
                level=1,
                current_xp=0,
                xp_to_next=xp_needed_for_next(1),
            )
            self.db.add(level)
            self.db.commit()
            self.db.refresh(level)

        return level

    def get_client_progress(self, client_id: UUID) -> dict:
        """Полный прогресс клиента"""
        level = self.get_or_create_level(client_id)
        achievements = self._get_achievements(client_id)
        rank = self._get_client_rank(client_id)

        # Рассчитываем прогресс бар
        xp_for_current = xp_for_level(level.level)
        xp_for_next = xp_for_level(level.level + 1)
        xp_progress = level.current_xp - xp_for_current
        xp_needed = xp_for_next - xp_for_current
        progress_pct = min(100, max(0, (xp_progress / xp_needed * 100))) if xp_needed > 0 else 100

        return {
            "client_id": str(client_id),
            "level": level.level,
            "level_title": self._get_level_title(level.level),
            "current_xp": level.current_xp,
            "xp_to_next": xp_for_next,
            "xp_progress": xp_progress,
            "xp_needed_for_next": xp_needed,
            "progress_percent": round(progress_pct, 1),
            "total_visits": level.total_visits,
            "total_workout_minutes": level.total_workout_minutes,
            "streak_days": level.streak_days,
            "max_streak_days": level.max_streak_days,
            "achievements_count": len(achievements),
            "achievements": achievements,
            "rank": rank,
            "next_rewards": self._get_next_rewards(level.level),
        }

    def get_leaderboard(self, limit: int = 20) -> list[dict]:
        """Топ клиентов по XP"""
        levels = self.db.execute(
            select(GamificationLevel)
            .order_by(desc(GamificationLevel.current_xp))
            .limit(limit)
        ).scalars().all()

        result = []
        for i, lvl in enumerate(levels, 1):
            client = self.db.execute(
                select(Client).where(Client.id == lvl.client_id)
            ).scalar_one_or_none()
            name = f"{client.first_name} {client.last_name}" if client else "Неизвестный"
            result.append({
                "rank": i,
                "client_id": lvl.client_id,
                "client_name": name,
                "level": lvl.level,
                "current_xp": lvl.current_xp,
                "total_visits": lvl.total_visits,
                "streak_days": lvl.streak_days,
                "achievements_count": lvl.achievements_count,
            })
        return result

    # ============================================================
    # ОБРАБОТКА ПОСЕЩЕНИЯ
    # ============================================================

    def process_visit(self, client_id: UUID, entry_at: datetime, exit_at: datetime | None = None) -> dict:
        """Начислить XP за посещение, проверить достижения"""
        level = self.get_or_create_level(client_id)

        # XP за визит
        xp_gained = XP_PER_VISIT
        level.total_visits += 1

        # XP за минуты тренировки
        minutes = 0
        if exit_at:
            minutes = int((exit_at - entry_at).total_seconds() / 60)
            workout_xp = int(minutes * XP_PER_MINUTE)
            xp_gained += workout_xp
            level.total_workout_minutes += minutes

        # Проверка streak
        streak_bonus = self._update_streak(level, entry_at)
        xp_gained += streak_bonus

        # Начисляем XP
        old_level = level.level
        level.current_xp += xp_gained

        # Проверяем повышение уровня
        level_ups = 0
        while level.level < MAX_LEVEL and level.current_xp >= xp_for_level(level.level + 1):
            level.level += 1
            level_ups += 1

        level.xp_to_next = xp_needed_for_next(level.level)
        self.db.commit()

        # Проверяем достижения
        new_achievements = self._check_achievements(client_id, level, entry_at)

        return {
            "xp_gained": xp_gained,
            "streak_bonus": streak_bonus,
            "total_xp": level.current_xp,
            "level": level.level,
            "levels_gained": level_ups,
            "workout_minutes": minutes,
            "new_achievements": new_achievements,
            "streak_days": level.streak_days,
        }

    def _update_streak(self, level: GamificationLevel, visit_date: datetime) -> int:
        """Обновить streak, вернуть бонус XP"""
        bonus = 0
        today = visit_date.date()

        if level.last_visit_at:
            last_date = level.last_visit_at.date()
            diff = (today - last_date).days

            if diff == 0:
                # Уже посещал сегодня — streak не меняется
                pass
            elif diff == 1:
                # Последовательный день — streak +
                level.streak_days += 1
                bonus = level.streak_days * STREAK_BONUS_XP
            else:
                # Прервали streak
                if level.streak_days > level.max_streak_days:
                    level.max_streak_days = level.streak_days
                level.streak_days = 1
                bonus = STREAK_BONUS_XP
        else:
            level.streak_days = 1
            bonus = STREAK_BONUS_XP

        level.last_visit_at = visit_date
        return bonus

    # ============================================================
    # ДОСТИЖЕНИЯ
    # ============================================================

    def _check_achievements(self, client_id: UUID, level: GamificationLevel, visit_time: datetime) -> list[dict]:
        """Проверить и выдать новые достижения"""
        new_achievements = []

        # Получаем уже имеющиеся
        existing_types = {
            row[0] for row in self.db.execute(
                select(Achievement.achievement_type)
                .where(Achievement.client_id == str(client_id))
            ).all()
        }

        checks = [
            ("first_visit", level.total_visits >= 1),
            ("week_warrior", level.streak_days >= 7),
            ("month_master", level.streak_days >= 30),
            ("centurion", level.total_visits >= 100),
            ("early_bird", level.total_visits >= 10 and visit_time.hour < 9),
            ("night_owl", level.total_visits >= 10 and visit_time.hour >= 20),
            (" marathon", level.total_workout_minutes >= 500),
        ]

        for ach_type, condition in checks:
            if condition and ach_type not in existing_types:
                ach_def = ACHIEVEMENT_DEFS.get(ach_type, {})
                achievement = Achievement(
                    client_id=str(client_id),
                    achievement_type=ach_type,
                    title=ach_def.get("title", ach_type),
                    description=ach_def.get("description", ""),
                    xp_reward=ach_def.get("xp", 0),
                    icon=ach_def.get("icon"),
                )
                self.db.add(achievement)
                level.current_xp += ach_def.get("xp", 0)
                level.achievements_count += 1
                new_achievements.append({
                    "type": ach_type,
                    "title": achievement.title,
                    "xp_reward": achievement.xp_reward,
                    "icon": achievement.icon,
                })

        if new_achievements:
            self.db.commit()

        return new_achievements

    def _get_achievements(self, client_id: UUID) -> list[dict]:
        """Все достижения клиента"""
        achievements = self.db.execute(
            select(Achievement)
            .where(Achievement.client_id == str(client_id))
            .order_by(desc(Achievement.created_at))
        ).scalars().all()

        return [
            {
                "type": a.achievement_type,
                "title": a.title,
                "description": a.description,
                "xp_reward": a.xp_reward,
                "icon": a.icon,
                "earned_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in achievements
        ]

    def _get_client_rank(self, client_id: UUID) -> int:
        """Место клиента в рейтинге"""
        client_level = self.db.execute(
            select(GamificationLevel).where(GamificationLevel.client_id == str(client_id))
        ).scalar_one_or_none()

        if not client_level:
            return 0

        rank = self.db.execute(
            select(func.count(GamificationLevel.id))
            .where(GamificationLevel.current_xp > client_level.current_xp)
        ).scalar() or 0

        return rank + 1

    @staticmethod
    def _get_level_title(level: int) -> str:
        """Название уровня"""
        titles = {
            1: "Новичок", 5: "Боец", 10: "Атлет", 15: "Спортсмен",
            20: "Профи", 25: "Эксперт", 30: "Мастер", 40: "Легенда", 50: "Чемпион"
        }
        for lvl in sorted(titles.keys(), reverse=True):
            if level >= lvl:
                return titles[lvl]
        return "Новичок"

    @staticmethod
    def _get_next_rewards(current_level: int) -> list[dict]:
        """Награды за ближайшие уровни"""
        rewards = []
        for lvl in range(current_level + 1, min(current_level + 4, MAX_LEVEL + 1)):
            if lvl % 5 == 0:
                rewards.append({"level": lvl, "reward": f"Бонусный абонемент на {lvl // 5} дней"})
            elif lvl % 10 == 0:
                rewards.append({"level": lvl, "reward": f"Персональная тренировка в подарок"})
        if not rewards:
            rewards.append({"level": current_level + 1, "reward": "+10 XP бонус"})
        return rewards[:3]
