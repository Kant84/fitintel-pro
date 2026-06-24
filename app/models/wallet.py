# app/models/wallet.py

from __future__ import annotations

from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Wallet(TimestampedUUIDMixin, Base):
    """
    Модель кошелька клиента.
    
    Хранит баланс клиента и замороженные средства.
    Каждый клиент имеет ровно один кошелёк.
    """
    
    __tablename__ = "wallets"

    # ID клиента (уникальный, один кошелёк на клиента)
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Текущий баланс
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    # Валюта (RUB, USD, EUR)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
    )
    
    # Замороженные средства (в спорах, ожидании возврата)
    frozen_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    # Связь с клиентом
    client = relationship("Client", back_populates="wallet")
    
    # Связь с транзакциями
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")
