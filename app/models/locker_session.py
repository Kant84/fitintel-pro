# app/models/locker_session.py

from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class LockerSession(TimestampedUUIDMixin, Base):
    """
    Модель сессии использования шкафчика.
    
    Для OFFLINE замков: создаётся при подсказке на инфотерминале.
    Для ONLINE замков: создаётся при регистрации браслета на терминале.
    """
    
    __tablename__ = "locker_sessions"

    # ID шкафчика
    locker_id: Mapped[str] = mapped_column(
        ForeignKey("lockers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # ID клиента
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # ID учётных данных (какой браслет/карта использовались)
    credential_id: Mapped[str | None] = mapped_column(
        ForeignKey("credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Тип замка (копия из lockers для быстрого доступа)
    lock_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # Время начала
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now,
    )
    
    # Время окончания
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Статус: ACTIVE, CLOSED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,
    )
    
    # ID инфотерминала (для OFFLINE замков — подсказка)
    info_terminal_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # ID терминала регистрации (для ONLINE замков)
    register_terminal_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Заметки
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Связи
    locker = relationship("Locker", back_populates="sessions")
    client = relationship("Client")
    credential = relationship("Credential")
