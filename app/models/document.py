# app/models/document.py

from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from uuid import uuid4
from app.db.base import Base, TimestampedUUIDMixin


class Document(Base, TimestampedUUIDMixin):
    """Документ клиента (договор, согласие, справка) в формате PDF"""

    __tablename__ = "documents"

    client_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Тип: contract, consent, medical, receipt, request
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # ID шаблона
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Название документа
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Имя файла
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # MIME-тип
    content_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)

    # Размер файла в байтах
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Данные PDF (blob)
    pdf_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Статус: draft, generated, signed, cancelled
    status: Mapped[str] = mapped_column(String(20), default="generated", nullable=False)

    # Дата подписания
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Кем подписан
    signed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Кем сгенерирован
    generated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Дополнительные данные
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Связь с клиентом
    client = relationship("Client", back_populates="documents")
