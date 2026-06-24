from datetime import date
from sqlalchemy import String, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class Client(TimestampedUUIDMixin, Base):
    __tablename__ = "clients"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    
    gender: Mapped[str] = mapped_column(String(50), nullable=False, default="НЕ_УКАЗАН")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    client_category: Mapped[str] = mapped_column(String(50), nullable=False, default="НЕ_УКАЗАНА")
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # ✅ Оставляем только существующие связи
    subscriptions = relationship("Subscription", back_populates="client", cascade="all, delete-orphan")
    events = relationship("ClientEvent", back_populates="client", cascade="all, delete-orphan")
    
    
    # Связь с посещениями
    visits = relationship("Visit", back_populates="client", cascade="all, delete-orphan")

    # Связь с учётными данными (QR, RFID)
    credentials = relationship("Credential", back_populates="client", cascade="all, delete-orphan")

    # Связь с привилегиями на шкафчики
    locker_privileges = relationship("LockerPrivilege", back_populates="client", cascade="all, delete-orphan")

    # Связь с сессиями шкафчиков
    locker_sessions = relationship("LockerSession", back_populates="client", cascade="all, delete-orphan")
    
    # Связь с кошельком
    wallet = relationship("Wallet", back_populates="client", uselist=False, cascade="all, delete-orphan")

    # Связь с платежами
    payments = relationship("Payment", back_populates="client", cascade="all, delete-orphan")

    # Геймификация (XP, уровни, достижения)

    achievements = relationship("Achievement", back_populates="client", cascade="all, delete-orphan")

    # Документы клиента
    documents = relationship("Document", back_populates="client")
    gamification_levels = relationship("GamificationLevel", back_populates="client", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="client", cascade="all, delete-orphan")
