import uuid

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class TelegramSettings(Base, TimestampedUUIDMixin):
    """Настройки Telegram-бота (singleton)"""

    __tablename__ = "telegram_settings"

    bot_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TelegramLink(Base, TimestampedUUIDMixin):
    """Привязка клиента к Telegram"""

    __tablename__ = "telegram_links"

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    telegram_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
