from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampedUUIDMixin, utc_now


class UserRole(TimestampedUUIDMixin, Base):
    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_id_role_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Пользователь, которому назначили роль
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="user_roles",
    )

    # Роль, назначенная пользователю
    role: Mapped["Role"] = relationship(
        "Role",
        foreign_keys=[role_id],
        back_populates="user_roles",
    )

    # Пользователь, который назначил роль
    assigned_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_by_user_id],
    )