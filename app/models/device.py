# app/models/device.py

from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Boolean, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Device(TimestampedUUIDMixin, Base):
    """
    Модель устройства (турникет, терминал, контроллер).
    ПОЛНОСТЬЮ ОПЦИОНАЛЬНА — если нет устройств, система работает через ручной ввод.
    """
    
    __tablename__ = "devices"

    # ==========================================================
    # ОСНОВНЫЕ ПОЛЯ
    # ==========================================================
    
    # Уникальный код устройства (например, "turnstile_01")
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Название устройства (для админки)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Тип устройства: turnstile, terminal, controller, reader
    device_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Производитель/модель: sigur, era, wirenboard, x1, generic
    manufacturer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Протокол: http, mqtt, modbus, serial, gpio, none
    protocol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="none",
    )
    
    # Адрес устройства (IP, COM-порт, MQTT topic)
    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Дополнительные параметры (JSON)
    config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    
    # Активно ли устройство
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    
    # Последний heartbeat (для мониторинга)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Зона, где находится устройство
    zone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Блокировка устройства
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Anti-passback включён
    anti_passback_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Рабочий график (JSON: {"start": "08:00", "end": "22:00"})
    work_schedule: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    
    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # ==========================================================
    # СВЯЗИ
    # ==========================================================
    
    # Связь с посещениями (через access_device_id)
    # visits = relationship("Visit", foreign_keys="Visit.access_device_id")
