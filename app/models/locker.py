# app/models/locker.py

from __future__ import annotations

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Locker(TimestampedUUIDMixin, Base):
    """
    Модель шкафчика в раздевалке.
    
    Поддерживает два типа замков:
    - OFFLINE: закрывается любым браслетом, инфотерминал только подсказывает номер
    - ONLINE: закрывается только при наличии привилегии, блокирует выход
    """
    
    __tablename__ = "lockers"

    # Номер шкафчика (A12, 101, и т.д.)
    number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Зона: мужская, женская, VIP
    zone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Тип замка: OFFLINE, ONLINE
    lock_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OFFLINE",
        index=True,
    )
    
    # Статус: FREE, OCCUPIED, BROKEN, MAINTENANCE
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="FREE",
        index=True,
    )
    
    # ID устройства замка (для ONLINE)
    device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Требуется ли привилегия (VIP/арендный шкаф)
    requires_privilege: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Заметки
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Связь с сессиями
    sessions = relationship("LockerSession", back_populates="locker")