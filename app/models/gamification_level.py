from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base, TimestampedUUIDMixin

class GamificationLevel(Base, TimestampedUUIDMixin):
    __tablename__ = "gamification_levels"
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    xp_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    xp_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    achievements_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    client = relationship("Client", back_populates="gamification_levels")

class Achievement(Base, TimestampedUUIDMixin):
    __tablename__ = "achievements"
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    client = relationship("Client", back_populates="achievements")
def xp_for_level(level: int) -> int:
    return level * 100
def xp_needed_for_next(level: int) -> int:
    return (level + 1) * 100

MAX_LEVEL = 100
