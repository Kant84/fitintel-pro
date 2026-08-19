# app/models/yookassa.py
"""
Модели YooKassa: сохранённые карты, webhook-события, возвраты.
"""

import uuid

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class SavedCard(Base, TimestampedUUIDMixin):
    """Сохранённая карта клиента для рекуррентных платежей"""
    __tablename__ = "saved_cards"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    payment_method_id: Mapped[str] = mapped_column(String(64), unique=True)
    card_last4: Mapped[str] = mapped_column(String(4), default="4242")
    card_type: Mapped[str] = mapped_column(String(32), default="Mir")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WebhookEvent(Base, TimestampedUUIDMixin):
    """Обработанные webhook-события (идемпотентность)"""
    __tablename__ = "yookassa_webhook_events"

    event_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text, default="{}")


class PaymentRefund(Base, TimestampedUUIDMixin):
    """Возвраты по платежам"""
    __tablename__ = "payment_refunds"

    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    external_refund_id: Mapped[str] = mapped_column(String(64), unique=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="succeeded")
    reason: Mapped[str] = mapped_column(String(255), default="")
