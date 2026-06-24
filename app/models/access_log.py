# app/models/access_log.py

from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class AccessLog(TimestampedUUIDMixin, Base):
    """
    Модель журнала попыток доступа.
    
    Фиксирует каждую попытку прохода через турникет/терминал.
    """
    
    __tablename__ = "access_logs"

    # ID устройства (турникет, терминал)
    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    # Значение учётных данных (QR или UID)
    credential_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    # Тип учётных данных (QR, RFID)
    credential_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # ID клиента (если найден)
    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Решение: ALLOW, DENY, ERROR
    decision: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Причина решения
    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Режим: online, offline
    mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="online",
    )
    
    # Использован ли кэш (для офлайн-режима)
    cache_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Сырые данные запроса от устройства
    request_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Данные ответа
    response_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Связь с клиентом
    client = relationship("Client", foreign_keys=[client_id])
