# app/models/online_session.py

from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class OnlineSession(Base, TimestampedUUIDMixin):
    """Онлайн-тренировка / видео-сессия"""

    __tablename__ = "online_sessions"

    # Название сессии
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Описание
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Тип: live (прямая трансляция), recorded (запись), scheduled (запланирована)
    session_type: Mapped[str] = mapped_column(String(20), nullable=False, default="recorded")

    # Категория: yoga, cardio, strength, stretching, pilates, hiit
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")

    # Уровень сложности: beginner, intermediate, advanced
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="beginner")

    # Длительность в минутах
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # URL видео или стриминга
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # URL превью (thumbnail)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ID тренера (ссылка на users)
    trainer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Время начала (для live/scheduled)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Время окончания
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Максимум участников (для live)
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Активна ли сессия
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Теги (JSON)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Связь с тренером
    trainer = relationship("User")

    # Связь с участниками
    participants = relationship("SessionParticipant", back_populates="session", cascade="all, delete-orphan")


class SessionParticipant(Base, TimestampedUUIDMixin):
    """Участник онлайн-сессии"""

    __tablename__ = "session_participants"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("online_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Статус: registered, attended, completed, cancelled
    status: Mapped[str] = mapped_column(String(20), default="registered", nullable=False)

    # Прогресс просмотра (%) для записей
    watch_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Время присоединения
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Время выхода
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Оценка (1-5)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Отзыв
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Связи
    session = relationship("OnlineSession", back_populates="participants")
    client = relationship("Client")
