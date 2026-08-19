from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
import uuid

class DynamicQRCode(Base):
    __tablename__ = "dynamic_qr_codes"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    qr_payload = Column(String(500), nullable=False)
    signature = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    qr_type = Column(String(20), nullable=False, server_default="CLIENT")
    max_uses = Column(Integer, nullable=False, server_default="1")
    uses_count = Column(Integer, nullable=False, server_default="0")
    guest_email = Column(String(255), nullable=True)
    client_ids = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
