# app/models/gamification_level.py

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class GamificationLevel(Base, TimestampedUUIDMixin):
    """Система уровней и XP клиента (геймификация)"""

    __tablename__ = "gamification_levels"

    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Текущий уровень (1-50)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # XP: текущий и для следующего уровня
    current_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_to_next: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Общая статистика
    total_visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_workout_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # серия дней подряд
    max_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    achievements_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Дата последнего посещения (для streak)
    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связь
    client = relationship("Client", back_populates="gamification")


class Achievement(Base, TimestampedUUIDMixin):
    """Достижения клиента"""

    __tablename__ = "achievements"

    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    achievement_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Связь
    client = relationship("Client")


# Расчёт XP для уровней: каждый уровень требует на 50 XP больше
LEVEL_XP_BASE = 100
LEVEL_XP_INCREMENT = 50
MAX_LEVEL = 50


def xp_for_level(level: int) -> int:
    """XP нужно для достижения уровня (кумулятивно)"""
    if level <= 1:
        return 0
    # Сумма арифметической прогрессии
    return (LEVEL_XP_BASE * (level - 1)) + (LEVEL_XP_INCREMENT * (level - 1) * (level - 2) // 2)


def xp_needed_for_next(current_level: int) -> int:
    """XP нужно для следующего уровня"""
    return LEVEL_XP_BASE + (current_level - 1) * LEVEL_XP_INCREMENT
