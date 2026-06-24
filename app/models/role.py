from __future__ import annotations

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin


class Role(TimestampedUUIDMixin, Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Связь с таблицей user_roles
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        foreign_keys="UserRole.role_id",
    )

    # Связь с таблицей role_permissions
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        foreign_keys="RolePermission.role_id",
    )

    @property
    def permissions(self) -> list["Permission"]:
        """
        Возвращает список прав роли в удобном виде:
        Role -> RolePermission -> Permission
        """
        return [
            item.permission
            for item in self.role_permissions
            if item.permission is not None
        ]
