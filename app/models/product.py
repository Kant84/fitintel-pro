# app/models/product.py
from sqlalchemy import Column, Numeric, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base, TimestampedUUIDMixin
import uuid

class Product(TimestampedUUIDMixin, Base):
    __tablename__ = "products"
    
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, default=0)
    category = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
