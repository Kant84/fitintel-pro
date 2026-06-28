import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base

class Service(Base):
    __tablename__ = "services"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)
    subcategory = Column(String(50))
    description = Column(Text)
    price = Column(Float, nullable=False)
    duration_minutes = Column(Integer)
    max_capacity = Column(Integer, default=1)
    trainer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    schedule = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ServiceBooking(Base):
    __tablename__ = "service_bookings"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    booking_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="BOOKED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
