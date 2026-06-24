# app/models/product.py
from sqlalchemy import Column, String, Text, Numeric, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    price = Column(Numeric(10, 2), nullable=False)
    cost_price = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")

    sales = relationship("TrainerSale", back_populates="product")
