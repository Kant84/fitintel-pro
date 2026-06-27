# app/models/sale.py
from sqlalchemy import Column, Numeric, String, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.base import TimestampedUUIDMixin
import uuid

class Sale(TimestampedUUIDMixin, Base):
    __tablename__ = "sales"
    
    cashier_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(20), nullable=False)  # CASH, CARD, WALLET
    items = Column(JSON, nullable=False)  # [{"product_id": "...", "quantity": 1, "price": 100}]
    discount_code = Column(String(50), nullable=True)
    status = Column(String(20), default="COMPLETED", nullable=False)  # COMPLETED, REFUNDED
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    
    cashier = relationship("User", backref="sales")
