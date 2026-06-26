import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.sql import func
from app.db.base import Base

class VideoAlert(Base):
    __tablename__ = "video_alerts"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    camera_id = Column(String(64), nullable=False)
    alert_type = Column(String(32), nullable=False)
    confidence = Column(Numeric(3,2), nullable=True)
    snapshot = Column(Text, nullable=True)
    zone = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_false_positive = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
