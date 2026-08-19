import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base, TimestampedUUIDMixin


class Equipment(Base, TimestampedUUIDMixin):
    """Фитнес-оборудование клуба (инвентарь, гарантия, обслуживание)"""

    __tablename__ = "equipment"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    serial_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # online | offline | maintenance
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="online")

    # Протокол интеграции: modbus_tcp | http_api | mqtt
    protocol: Mapped[str] = mapped_column(String(20), nullable=False, default="http_api")
    connection_string: Mapped[str | None] = mapped_column(String(500), nullable=True)

    purchase_date = mapped_column(DateTime(timezone=True), nullable=True)
    warranty_until = mapped_column(DateTime(timezone=True), nullable=True)

    maintenance_records = relationship(
        "MaintenanceRecord", back_populates="equipment", cascade="all, delete-orphan"
    )


class MaintenanceRecord(Base, TimestampedUUIDMixin):
    """Запись обслуживания оборудования"""

    __tablename__ = "maintenance_records"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    scheduled_date = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)

    equipment = relationship("Equipment", back_populates="maintenance_records")
