# app/models/marketing_campaign.py

import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampedUUIDMixin


class MarketingCampaign(Base, TimestampedUUIDMixin):
    """Маркетинговая кампания (SMS/email рассылка)"""

    __tablename__ = "marketing_campaigns"

    # Название кампании
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Тип: sms, email, push
    campaign_type: Mapped[str] = mapped_column(String(20), default="sms", nullable=False)

    # Канал: sms, email
    channel: Mapped[str] = mapped_column(String(20), default="sms", nullable=False)

    # ID сегмента (new, active, sleeping, churn и т.д.)
    segment_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Шаблон сообщения
    message_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Тема (для email)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Время запланированной отправки
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Время фактической отправки
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Статус: draft, scheduled, sent, cancelled
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)

    # Кем создана
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Результаты отправки
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
