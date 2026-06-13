from __future__ import annotations

from decimal import Decimal
from sqlalchemy import String, Boolean, Integer, Numeric, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Tariff(TimestampedUUIDMixin, Base):
    __tablename__ = "tariffs"

    __table_args__ = (
        UniqueConstraint("code", name="uq_tariffs_code"),
        UniqueConstraint("name", name="uq_tariffs_name"),
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="RUB",
    )

    duration_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    visit_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
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

    # ✅ ДОБАВИТЬ СВЯЗЬ С АБОНЕМЕНТАМИ
    subscriptions = relationship("Subscription", back_populates="tariff", cascade="all, delete-orphan")