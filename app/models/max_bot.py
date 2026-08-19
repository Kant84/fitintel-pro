import uuid

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class MaxBotSettings(Base, TimestampedUUIDMixin):
    """Настройки MAX-бота (singleton)"""

    __tablename__ = "max_bot_settings"

    bot_token: Mapped[str | None] = mapped_column(String(300), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MaxLink(Base, TimestampedUUIDMixin):
    """Привязка клиента к MAX (user_id в мессенджере MAX)"""

    __tablename__ = "max_links"

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    max_user_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    max_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
