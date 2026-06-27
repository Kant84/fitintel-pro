# app/models/discount.py
from sqlalchemy import Column, Numeric, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base, TimestampedUUIDMixin
import uuid

class Discount(TimestampedUUIDMixin, Base):
    __tablename__ = "discounts"
    
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    discount_type = Column(String(20), nullable=False)  # PERCENT, FIXED
    value = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
