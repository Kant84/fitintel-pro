# app/models/export.py
from sqlalchemy import Column, String, Integer, BigInteger, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    user_id = Column(UUID(as_uuid=True))
    entity = Column(String(50), nullable=False)
    format = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    file_path = Column(String(500))
    file_size = Column(BigInteger)
    row_count = Column(Integer)
    error_message = Column(Text)
    filters = Column(JSON)
    created_at = Column(TIMESTAMP, default="now()")
    completed_at = Column(TIMESTAMP)
