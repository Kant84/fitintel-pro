# app/models/visit.py

from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Visit(TimestampedUUIDMixin, Base):
    """
    Модель посещения клиента.
    Фиксирует вход и выход, списание визитов из абонемента.
    """
    
    __tablename__ = "visits"

    # ==========================================================
    # СВЯЗИ С ДРУГИМИ ТАБЛИЦАМИ
    # ==========================================================

    # ID клиента (обязательно)
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ID абонемента (опционально — может быть разовое посещение)
    subscription_id: Mapped[str | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Кто обработал (для ручных операций)
    processed_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ==========================================================
    # ВРЕМЕННЫЕ МЕТКИ
    # ==========================================================

    # Время входа
    entry_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Время выхода (может быть NULL, если клиент ещё внутри)
    exit_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Длительность пребывания в минутах (вычисляется при выходе)
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ==========================================================
    # ИНФОРМАЦИЯ О ДОСТУПЕ
    # ==========================================================

    # Способ доступа: QR, RFID, MANUAL, OVERRIDE
    access_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="QR",
        index=True,
    )

    # ID устройства (турникет, терминал)
    access_device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Был ли доступ разрешён
    access_granted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Причина отказа (если доступ запрещён)
    access_denied_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ==========================================================
    # СТАТУС И ЗОНА
    # ==========================================================

    # Статус: ACTIVE (внутри), COMPLETED (вышел), CANCELLED (отменено)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,
    )

    # Зона клуба: GYM, POOL, STUDIO, ENTRANCE
    zone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ==========================================================
    # ДОПОЛНИТЕЛЬНО
    # ==========================================================

    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # СВЯЗИ ДЛЯ ORM
    # ==========================================================

    # Связь с клиентом
    client = relationship("Client", back_populates="visits")

    # Связь с абонементом
    subscription = relationship("Subscription", back_populates="visits")

    # Связь с пользователем, который обработал (для ручных операций)
    processed_by = relationship("User", foreign_keys=[processed_by_user_id])