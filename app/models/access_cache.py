# app/models/access_cache.py

from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampedUUIDMixin


class AccessCache(TimestampedUUIDMixin, Base):
    """
    Модель кэша прав доступа для офлайн-режима.
    
    Терминалы/турникеты скачивают этот кэш и используют при отсутствии интернета.
    """
    
    __tablename__ = "access_cache"

    # Учётные данные (QR-код или UID RFID)
    credential_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Результат проверки
    access_granted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Имя клиента (для приветствия на терминале)
    client_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Статус абонемента
    subscription_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # Осталось посещений
    visits_left: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # Дата окончания абонемента
    subscription_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Начало действия кэша
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    # Окончание действия кэша
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    
    # Версия кэша (увеличивается при изменении прав)
    cache_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    
    # ID устройства, для которого создан кэш
    device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
