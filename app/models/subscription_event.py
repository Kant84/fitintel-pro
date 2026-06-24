# app/models/subscription_event.py

# app/models/subscription_event.py

from uuid import UUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class SubscriptionEvent(TimestampedUUIDMixin, Base):
    """
    Модель события изменения статуса абонемента.
    Хранит историю всех изменений жизненного цикла.
    """
    
    __tablename__ = "subscription_events"

    # ID абонемента
    subscription_id: Mapped[str] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Предыдущий статус (может быть None для первого события)
    from_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Новый статус
    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Причина изменения
    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Кто выполнил действие (ID пользователя)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),  # ← используем PG_UUID, а не UUID
        nullable=True,
        index=True,
    )

    # Связь с абонементом
    subscription = relationship("Subscription", back_populates="status_events")
