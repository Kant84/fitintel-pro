# app/models/notification.py
from sqlalchemy import Column, String, Text, ARRAY, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    channel = Column(String(20))
    subject = Column(String(200))
    body_template = Column(Text, nullable=False)
    variables = Column(ARRAY(String))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    client_id = Column(UUID(as_uuid=True))
    channel = Column(String(20), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("notification_templates.id", ondelete="SET NULL"))
    subject = Column(String(200))
    body = Column(Text)
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    sent_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default="now()")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    endpoint = Column(Text, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    updated_at = Column(TIMESTAMP, default="now()")
