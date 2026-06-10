# app\models\client_event.py
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin

class ClientEvent(TimestampedUUIDMixin, Base):
    __tablename__ = "client_events"

    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        nullable=True,
        index=True,
    )

    # Связь с клиентом
    client = relationship("Client", back_populates="events")