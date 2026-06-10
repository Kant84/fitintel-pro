# app/models/locker_privilege.py

from __future__ import annotations

from datetime import date
from sqlalchemy import String, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class LockerPrivilege(TimestampedUUIDMixin, Base):
    """
    Модель привилегий на шкафчики.
    
    Назначается клиентам для доступа к:
    - VIP шкафчикам
    - Арендным шкафчикам
    """
    
    __tablename__ = "locker_privileges"

    # ID клиента
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Тип шкафчика: VIP, RENTAL
    locker_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Дата начала действия
    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )
    
    # Дата окончания действия (NULL = бессрочно)
    valid_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    
    # Кто выдал
    issued_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Заметки
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Связи
    client = relationship("Client", back_populates="locker_privileges")
    issued_by = relationship("User", foreign_keys=[issued_by_user_id])
    