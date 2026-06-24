# app/models/credential.py

from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import String, ForeignKey, Date, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Credential(TimestampedUUIDMixin, Base):
    """
    Модель учётных данных доступа.
    
    Хранит:
    - QR-коды для мобильного телефона
    - RFID-браслеты/карты
    """
    
    __tablename__ = "credentials"

    # ==========================================================
    # СВЯЗИ
    # ==========================================================
    
    # ID клиента (обязательно)
    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # ID пользователя, который выдал учётные данные
    issued_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # ==========================================================
    # ТИП И ЗНАЧЕНИЕ
    # ==========================================================
    
    # Тип: QR, RFID
    credential_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Значение: QR-код (строка) или UID RFID-метки
    credential_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # ==========================================================
    # СТАТУС И СРОК ДЕЙСТВИЯ
    # ==========================================================
    
    # Статус: ACTIVE, BLOCKED, EXPIRED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,
    )
    
    # Дата начала действия
    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )
    
    # Дата окончания действия (NULL = без ограничения)
    valid_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )
    
    # ==========================================================
    # ДЛЯ QR-КОДОВ
    # ==========================================================
    
    # Версия QR-кода
    qr_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # Формат QR-кода: jwt, uuid
    qr_format: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="jwt",
    )
    
    # ==========================================================
    # ДЛЯ RFID-МЕТОК
    # ==========================================================
    
    # Производитель метки
    rfid_manufacturer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Модель метки
    rfid_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # ==========================================================
    # ДЛЯ FACE ID
    # ==========================================================
    
    # Уверенность распознавания (0.0 - 1.0)
    face_confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    
    # Шаблон лица (base64 или ссылка на хранилище)
    face_template: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # ДОПОЛНИТЕЛЬНО
    # ==========================================================
    
    # Дата выдачи
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now,
    )
    
    # Дополнительные параметры (JSON: MIFARE, конфиг устройства)
    config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )

    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # ==========================================================
    # СВЯЗИ ДЛЯ ORM
    # ==========================================================
    
    client = relationship("Client", back_populates="credentials")
    issued_by = relationship("User", foreign_keys=[issued_by_user_id])
