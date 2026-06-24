# app/models/receipt.py

from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Receipt(TimestampedUUIDMixin, Base):
    """
    Модель чека (фискального или нефискального).
    
    Связан с платежом, может быть отправлен клиенту.
    """
    
    __tablename__ = "receipts"

    # ID платежа
    payment_id: Mapped[str] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Номер чека (внутренний)
    receipt_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Тип чека: SALE, REFUND
    receipt_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Фискальный признак (от ОФД)
    fiscal_sign: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Номер фискального документа
    fiscal_document_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # Дата фискального документа
    fiscal_document_date: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    
    # Ссылка на чек в ОФД
    ofd_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # QR-код чека
    qr_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Сырые данные от ОФД
    raw_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Email для отправки
    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Телефон для отправки
    customer_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # Был ли отправлен чек
    is_sent: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    
    # Связь с платежом
    payment = relationship("Payment", back_populates="receipt")
