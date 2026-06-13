# app/models/payment.py

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Payment(TimestampedUUIDMixin, Base):
    """
    Модель платежа.
    
    Фиксирует все финансовые поступления.
    """
    
    __tablename__ = "payments"

    # ID клиента
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    # Сумма платежа
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    # Валюта
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
    )
    
    # Способ оплаты: CASH, CARD, ONLINE, BALANCE
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Статус: PENDING, COMPLETED, FAILED, REFUNDED, CANCELLED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True,
    )
    
    # ID платежа во внешней системе (эквайринг)
    external_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    
    # Платёжная система: SBERBANK, TINKOFF, YOOMONEY, etc.
    payment_system: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # Дата подтверждения платежа
    paid_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    
    # Кто создал платёж
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Связи
    client = relationship("Client", back_populates="payments")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    receipt = relationship("Receipt", back_populates="payment", uselist=False, cascade="all, delete-orphan")