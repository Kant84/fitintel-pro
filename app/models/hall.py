# app/models/hall.py
from sqlalchemy import Column, String, Integer, Numeric, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Hall(Base):
    __tablename__ = "halls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50))
    capacity = Column(Integer, default=20)
    area_sqm = Column(Numeric(6, 2))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")

    schedules = relationship("TrainerSchedule", back_populates="hall")
