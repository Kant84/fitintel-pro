# app/models/audit.py

# Импорт uuid для генерации UUID-идентификаторов.
import uuid

# Импорт datetime для хранения времени создания записи.
from datetime import datetime

# Импорт SQLAlchemy-типов.
from sqlalchemy import DateTime, JSON, String

# Импорт UUID-типа PostgreSQL.
from sqlalchemy.dialects.postgresql import UUID

# Импорт ORM-инструментов.
from sqlalchemy.orm import Mapped, mapped_column

# Импорт базового класса всех ORM-моделей проекта.
from app.db.base import Base


class AuditLog(Base):
    """
    Универсальная модель журнала аудита.

    Важно:
    здесь не используем TimestampedUUIDMixin,
    потому что в таблице audit_logs нет поля updated_at.
    """

    # Имя таблицы в базе данных.
    __tablename__ = "audit_logs"

    # Уникальный идентификатор записи аудита.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ID пользователя, который выполнил действие.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Тип действия.
    # Примеры:
    # rbac.role.assigned
    # rbac.role.revoked
    # rbac.role_permission.added
    # rbac.role_permission.removed
    action: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # Тип сущности, над которой произошло действие.
    # Примеры:
    # user_role
    # role_permission
    # role
    # permission
    entity_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # ID основной сущности, если он есть.
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # ID целевого пользователя, если действие связано с пользователем.
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # ID роли, если событие связано с ролью.
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # ID permission, если событие связано с permission.
    permission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Статус операции.
    # Возможные значения:
    # success / denied / error
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # Человекочитаемое сообщение.
    message: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    # Состояние объекта до изменения.
    before_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Состояние объекта после изменения.
    after_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Время создания записи аудита.
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )