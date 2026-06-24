# app/models/cash_desk_session.py

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin

class CashDeskSession(TimestampedUUIDMixin, Base):
    """
    Модель кассовой смены.
    
    Каждая смена открывается кассиром и закрывается с отчётом.
    """
    
    __tablename__ = "cash_desk_sessions"

    # Номер смены (инкрементальный)
    session_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    
    # ID кассира
    cashier_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    # Время открытия
    opened_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )
    
    # Время закрытия
    closed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    
    # Начальный остаток
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    # Конечный остаток
    closing_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    
    # Наличные поступления за смену
    cash_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    # Наличные выплаты за смену
    cash_outcome: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    # Безналичные поступления за смену
    card_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    # Ожидаемая наличность (расчётная)
    expected_cash: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    
    # Фактическая наличность
    actual_cash: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    
    # Расхождение
    discrepancy: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    
    # Статус: OPEN, CLOSED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OPEN",
        index=True,
    )
    
    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Связь с кассиром
    cashier = relationship("User", foreign_keys=[cashier_user_id])
    
    # Связь с операциями
    operations = relationship("CashOperation", back_populates="session", cascade="all, delete-orphan")
