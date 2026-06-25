# app/models/integration.py
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    provider = Column(String(50), nullable=False)
    category = Column(String(30), nullable=False)
    is_active = Column(Boolean, default=False)
    config = Column(JSON, default={})
    webhook_url = Column(String(500))
    last_sync_at = Column(TIMESTAMP)
    sync_status = Column(String(20), default="never")
    last_error = Column(Text)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")


class IntegrationSyncLog(Base):
    __tablename__ = "integration_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    provider = Column(String(50), nullable=False)
    category = Column(String(30), nullable=False)
    direction = Column(String(20))
    entity = Column(String(50))
    records_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    details = Column(JSON)
    created_at = Column(TIMESTAMP, default="now()")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    client_id = Column(UUID(as_uuid=True))
    provider = Column(String(50), nullable=False)
    external_id = Column(String(200))
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    status = Column(String(20), default="pending")
    payment_method = Column(String(50))
    description = Column(Text)
    meta_data = Column(JSON)
    paid_at = Column(TIMESTAMP)
    refunded_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)
    club_id = Column(Integer)
    payload = Column(JSON)
    headers = Column(JSON)
    signature = Column(String(500))
    processed = Column(Boolean, default=False)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default="now()")
