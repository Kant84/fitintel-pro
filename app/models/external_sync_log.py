# app/models/external_sync_log.py

from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, JSON, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampedUUIDMixin


class ExternalSyncLog(TimestampedUUIDMixin, Base):
    """
    Модель журнала синхронизации с внешними системами.
    
    Фиксирует обмен данными с:
    - 1С (бухгалтерия)
    - СКУД (система контроля доступа)
    - Файловыми серверами
    """
    
    __tablename__ = "external_sync_logs"

    # Тип системы: ONEC, SKUD, FILE_SERVER
    system_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Операция: CLIENT_IMPORT, ACCESS_SYNC, LOCKER_STATUS
    operation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    # Тип сущности: client, subscription, locker, visit
    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # ID сущности
    entity_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Статус: PENDING, SUCCESS, FAILED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True,
    )
    
    # Данные запроса
    request_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Данные ответа
    response_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Текст ошибки
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Количество попыток
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Дата обработки
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )