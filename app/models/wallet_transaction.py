# app/models/wallet_transaction.py

from __future__ import annotations

from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class WalletTransaction(TimestampedUUIDMixin, Base):
    """
    Модель транзакции кошелька.
    
    Фиксирует каждое изменение баланса.
    """
    
    __tablename__ = "wallet_transactions"

    # ID кошелька
    wallet_id: Mapped[str] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Тип транзакции: DEPOSIT, WITHDRAW, FREEZE, UNFREEZE
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Сумма
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    # Баланс до операции
    balance_before: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    # Баланс после операции
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    # Описание транзакции
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Тип связанной сущности: payment, subscription, service, refund
    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    
    # ID связанной сущности
    reference_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    
    # Кто создал транзакцию
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Связи
    wallet = relationship("Wallet", back_populates="transactions")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
