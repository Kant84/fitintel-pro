# app/models/subscription.py

from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Subscription(TimestampedUUIDMixin, Base):
    __tablename__ = "subscriptions"

    # ==========================================================
    # ОСНОВНЫЕ ПОЛЯ
    # ==========================================================

    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    tariff_id: Mapped[str] = mapped_column(
        ForeignKey("tariffs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    visit_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    visits_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_unlimited: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # НОВЫЕ ПОЛЯ ДЛЯ ЖИЗНЕННОГО ЦИКЛА
    # ==========================================================

    # Заморозка
    frozen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    frozen_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    freeze_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Продление и отмена
    auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    last_renewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # СВЯЗИ
    # ==========================================================

    # Связь с клиентом
    client = relationship("Client", back_populates="subscriptions")

    # Связь с тарифом
    tariff = relationship("Tariff", back_populates="subscriptions")

    # Связь с историей статусов
    status_events = relationship(
        "SubscriptionEvent",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    # ✅ ДОБАВИТЬ СВЯЗЬ С ПОСЕЩЕНИЯМИ
    visits = relationship(
        "Visit",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )