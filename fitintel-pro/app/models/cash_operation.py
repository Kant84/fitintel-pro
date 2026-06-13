# app/models/cash_operation.py

from __future__ import annotations

from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class CashOperation(TimestampedUUIDMixin, Base):
    """
    Модель кассовой операции.
    
    Фиксирует каждое движение наличных и безналичных средств.
    """
    
    __tablename__ = "cash_operations"

    # ID смены
    session_id: Mapped[str] = mapped_column(
        ForeignKey("cash_desk_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Тип: INCOME, OUTCOME
    operation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Сумма
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    # Способ оплаты: CASH, CARD
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # Тип связанной сущности: payment, refund
    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # ID связанной сущности
    reference_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Описание
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Кто создал операцию
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Связи
    session = relationship("CashDeskSession", back_populates="operations")
    created_by = relationship("User", foreign_keys=[created_by_user_id])