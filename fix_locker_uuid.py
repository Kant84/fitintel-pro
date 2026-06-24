# fix_locker_uuid.py
with open('app/models/locker.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_model = '''# app/models/locker.py
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

new_model = '''# app/models/locker.py
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Locker(Base):
    """Модель шкафчика (E11)"""

    __tablename__ = "lockers"

    id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
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

if old_model in content:
    with open('app/models/locker.py', 'w', encoding='utf-8') as f:
        f.write(new_model)
    print("Модель Locker исправлена с UUID!")
else:
    print("ERROR: Не найдена модель")
