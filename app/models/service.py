from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.trainer import TrainerProfile
    from app.models.client import Client


class ServiceCategory(str, enum.Enum):
    """Категории услуг фитнес-клуба."""
    GYM_ACCESS = "GYM_ACCESS"
    GROUP_CLASS = "GROUP_CLASS"
    PERSONAL_TRAINER = "PERSONAL_TRAINER"
    MASSAGE = "MASSAGE"
    SAUNA = "SAUNA"
    POOL = "POOL"
    YOGA = "YOGA"
    PILATES = "PILATES"
    NUTRITION = "NUTRITION"
    PHYSIO = "PHYSIO"
    OTHER = "OTHER"


class Service(Base):
    """Услуга клуба: групповые занятия, персоналки, массаж и т.д."""

    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[ServiceCategory] = mapped_column(String(20), default=ServiceCategory.OTHER)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_capacity: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    trainer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="SET NULL"), nullable=True
    )
    trainer: Mapped[Optional["TrainerProfile"]] = relationship("TrainerProfile", lazy="joined")

    schedule: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    """JSON: {"days": [1,3,5], "time_slots": [{"time": "10:00", "capacity": 10}, ...]}"""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bookings: Mapped[List["ServiceBooking"]] = relationship("ServiceBooking", back_populates="service")

    def __repr__(self) -> str:
        return f"<Service {self.name} ({self.category.value})>"


class ServiceBooking(Base):
    """Запись клиента на услугу."""

    __tablename__ = "service_bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    service: Mapped["Service"] = relationship("Service", back_populates="bookings", lazy="joined")
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    client: Mapped["Client"] = relationship("Client", lazy="joined")
    booking_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="BOOKED")
    """BOOKED / CONFIRMED / PAID / COMPLETED / CANCELLED / AUTO_CANCELLED / NO_SHOW"""
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Волна 5: жизненный цикл брони ---
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pinged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="api")
    """api / MAX / reception / widget"""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("service_id", "client_id", "booking_date", name="uq_service_booking"),
    )

    def __repr__(self) -> str:
        return f"<ServiceBooking {self.client_id} -> {self.service_id} @ {self.booking_date}>"