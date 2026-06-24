# app/models/chat.py
"""
MAX Messenger — модели чата.
Чаты, сообщения, прочтения, вложения.
"""

import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampedUUIDMixin


class ChatRoom(Base, TimestampedUUIDMixin):
    """Комната чата (личный или групповой)"""

    __tablename__ = "chat_rooms"

    # Название (для групповых)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Тип: direct (1-on-1), group, support
    room_type: Mapped[str] = mapped_column(String(20), default="direct", nullable=False)

    # Описание (для групповых)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Аватар
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Создатель
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Активна ли
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Закреплённое сообщение
    pinned_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Связи
    members = relationship("ChatMember", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")


class ChatMember(Base, TimestampedUUIDMixin):
    """Участник чата"""

    __tablename__ = "chat_members"

    room_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # user_id или client_id
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)

    # Роль: admin, member, viewer
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)

    # Последнее прочитанное сообщение
    last_read_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Время последнего прочтения
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Количество непрочитанных
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Связи
    room = relationship("ChatRoom", back_populates="members")

    __table_args__ = (
        Index("idx_chat_member", "room_id", "user_id", "client_id", unique=True),
    )


class ChatMessage(Base, TimestampedUUIDMixin):
    """Сообщение в чате"""

    __tablename__ = "chat_messages"

    room_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Отправитель
    sender_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sender_client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    sender_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Тип: text, image, file, voice, system
    message_type: Mapped[str] = mapped_column(String(20), default="text", nullable=False)

    # Текст
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Вложение
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Ответ на сообщение
    reply_to_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Отредактировано
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Удалено
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Связи
    room = relationship("ChatRoom", back_populates="messages")
    reads = relationship("ChatMessageRead", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_chat_msg_room_created", "room_id", "created_at"),
    )


class ChatMessageRead(Base, TimestampedUUIDMixin):
    """Факт прочтения сообщения"""

    __tablename__ = "chat_message_reads"

    message_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Кто прочитал
    reader_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reader_client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)

    # Связи
    message = relationship("ChatMessage", back_populates="reads")
