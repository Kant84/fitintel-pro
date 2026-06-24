# fix_locker_model.py
with open('app/models/locker.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем LockerSession, оставляем только Locker
old_content = '''# app/models/locker.py
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Locker(Base):
    """Модель шкафчика (E11)"""

    __tablename__ = "lockers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lock_type: Mapped[str] = mapped_column(String(50), nullable=False, default="OFFLINE")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="FREE")
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requires_privilege: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Отношения
    sessions: Mapped[list["LockerSession"]] = relationship("LockerSession", back_populates="locker", cascade="all, delete-orphan")


class LockerSession(Base):
    """Модель сессии шкафчика (E11)"""

    __tablename__ = "locker_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    locker_id: Mapped[str] = mapped_column(ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("credentials.id", ondelete="SET NULL"), nullable=True)
    lock_type: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    info_terminal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    register_terminal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Отношения
    locker: Mapped["Locker"] = relationship("Locker", back_populates="sessions")'''

new_content = '''# app/models/locker.py
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Locker(Base):
    """Модель шкафчика (E11)"""

    __tablename__ = "lockers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lock_type: Mapped[str] = mapped_column(String(50), nullable=False, default="OFFLINE")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="FREE")
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requires_privilege: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Отношения
    sessions: Mapped[list["LockerSession"]] = relationship("LockerSession", back_populates="locker", cascade="all, delete-orphan")'''

if old_content in content:
    with open('app/models/locker.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Модель Locker исправлена!")
else:
    print("ERROR: Не найдено содержимое")
