from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import date
import uuid

from app.db.base import Base, TimestampedUUIDMixin

MAX_LEVEL = 100


def xp_for_level(level: int) -> int:
    return level * 100


def xp_needed_for_next(level: int) -> int:
    return (level + 1) * 100


class GamificationLevel(Base, TimestampedUUIDMixin):
    __tablename__ = "gamification_levels"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    xp_to_next: Mapped[int] = mapped_column(Integer, nullable=False, default=xp_needed_for_next(1))
    total_visits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_workout_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_visit_date = mapped_column(Date, nullable=True)
    achievements_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    client = relationship("Client", back_populates="gamification_levels")


class Achievement(Base, TimestampedUUIDMixin):
    __tablename__ = "achievements"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    achievement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)

    client = relationship("Client", back_populates="achievements")


class AchievementDef(Base, TimestampedUUIDMixin):
    __tablename__ = "achievement_defs"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)  # visits_count | streak_days | workout_minutes
    condition_value: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)


class Reward(Base, TimestampedUUIDMixin):
    __tablename__ = "gamification_rewards"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    level_required: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RewardActivation(Base, TimestampedUUIDMixin):
    __tablename__ = "reward_activations"

    reward_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gamification_rewards.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class XPRule(Base, TimestampedUUIDMixin):
    __tablename__ = "xp_rules"

    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
