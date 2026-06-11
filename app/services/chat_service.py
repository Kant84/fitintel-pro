# app/services/chat_service.py
"""
MAX Messenger — сервис чата.
Личные сообщения, группы, история, прочтения.
"""

from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, WebSocket
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, and_, or_

from app.models.chat import ChatRoom, ChatMember, ChatMessage, ChatMessageRead
from app.models.user import User
from app.models.client import Client


class ChatService:
    """MAX Messenger — чат для тренеров и клиентов"""

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # КОМНАТЫ
    # ============================================================

    def create_direct_room(self, user_a_id: str, user_a_type: str, user_b_id: str, user_b_type: str) -> ChatRoom:
        """Создать или найти личный чат между двумя пользователями"""
        # Ищем существующий direct-чат
        existing = self._find_direct_room(user_a_id, user_a_type, user_b_id, user_b_type)
        if existing:
            return existing

        room = ChatRoom(
            id=str(uuid4()),
            room_type="direct",
            created_by=user_a_id if user_a_type == "user" else None,
            is_active=True,
        )
        self.db.add(room)
        self.db.flush()

        # Добавляем обоих участников
        self._add_member(room.id, user_a_id, user_a_type, "member")
        self._add_member(room.id, user_b_id, user_b_type, "member")

        # Системное сообщение
        self._add_system_message(room.id, "Чат создан")

        self.db.commit()
        return room

    def create_group_room(self, name: str, creator_id: str, creator_type: str, member_ids: list[dict], description: str = "") -> ChatRoom:
        """Создать групповой чат"""
        room = ChatRoom(
            id=str(uuid4()),
            name=name,
            room_type="group",
            description=description,
            created_by=creator_id if creator_type == "user" else None,
            is_active=True,
        )
        self.db.add(room)
        self.db.flush()

        # Создатель как админ
        self._add_member(room.id, creator_id, creator_type, "admin")

        # Остальные участники
        for m in member_ids:
            self._add_member(room.id, m["id"], m["type"], "member")

        self._add_system_message(room.id, f"Группа '{name}' создана")
        self.db.commit()
        return room

    def get_room(self, room_id: str) -> ChatRoom:
        """Получить комнату"""
        room = self.db.execute(select(ChatRoom).where(ChatRoom.id == room_id)).scalar_one_or_none()
        if not room:
            raise HTTPException(status_code=404, detail="Чат не найден")
        return room

    def list_user_rooms(self, user_id: str, user_type: str) -> list[dict]:
        """Список чатов пользователя"""
        # Находим room_ids где пользователь участник
        if user_type == "user":
            member_filter = ChatMember.user_id == user_id
        else:
            member_filter = ChatMember.client_id == user_id

        members = self.db.execute(
            select(ChatMember).where(member_filter).where(ChatMember.room_id.isnot(None))
        ).scalars().all()

        room_ids = [m.room_id for m in members]
        if not room_ids:
            return []

        rooms = self.db.execute(
            select(ChatRoom).where(ChatRoom.id.in_(room_ids)).where(ChatRoom.is_active == True)
            .order_by(desc(ChatRoom.updated_at))
        ).scalars().all()

        result = []
        for room in rooms:
            # Последнее сообщение
            last_msg = self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.room_id == room.id)
                .where(ChatMessage.is_deleted == False)
                .order_by(desc(ChatMessage.created_at))
            ).scalars().first()

            # Непрочитанные
            unread = self.db.execute(
                select(ChatMember.unread_count).where(ChatMember.room_id == room.id).where(member_filter)
            ).scalar() or 0

            result.append({
                "id": room.id,
                "name": room.name or "Личный чат",
                "type": room.room_type,
                "last_message": {
                    "text": last_msg.content[:50] if last_msg else "",
                    "sender": last_msg.sender_name if last_msg else "",
                    "time": last_msg.created_at.isoformat() if last_msg else None,
                },
                "unread_count": unread,
                "updated_at": room.updated_at.isoformat() if room.updated_at else None,
            })
        return result

    # ============================================================
    # СООБЩЕНИЯ
    # ============================================================

    def send_message(self, room_id: str, sender_id: str, sender_type: str, sender_name: str,
                     content: str, message_type: str = "text", reply_to_id: str = None,
                     attachment_url: str = None, attachment_name: str = None) -> ChatMessage:
        """Отправить сообщение"""
        room = self.get_room(room_id)

        # Проверяем что отправитель в чате
        if not self._is_member(room_id, sender_id, sender_type):
            raise HTTPException(status_code=403, detail="Вы не участник этого чата")

        msg = ChatMessage(
            id=str(uuid4()),
            room_id=room_id,
            sender_user_id=sender_id if sender_type == "user" else None,
            sender_client_id=sender_id if sender_type == "client" else None,
            sender_name=sender_name,
            message_type=message_type,
            content=content,
            reply_to_id=reply_to_id,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
        )
        self.db.add(msg)

        # Увеличиваем счётчик непрочитанных для остальных
        self.db.execute(
            ChatMember.__table__.update()
            .where(ChatMember.room_id == room_id)
            .where(ChatMember.user_id != sender_id if sender_type == "user" else ChatMember.client_id != sender_id)
            .values(unread_count=ChatMember.unread_count + 1)
        )

        self.db.commit()
        return msg

    def get_messages(self, room_id: str, user_id: str, user_type: str, limit: int = 50, before_id: str = None) -> list[dict]:
        """История сообщений"""
        if not self._is_member(room_id, user_id, user_type):
            raise HTTPException(status_code=403, detail="Доступ запрещён")

        query = select(ChatMessage).where(ChatMessage.room_id == room_id).where(ChatMessage.is_deleted == False)

        if before_id:
            before_msg = self.db.execute(select(ChatMessage).where(ChatMessage.id == before_id)).scalar_one_or_none()
            if before_msg:
                query = query.where(ChatMessage.created_at < before_msg.created_at)

        messages = self.db.execute(query.order_by(desc(ChatMessage.created_at)).limit(limit)).scalars().all()

        # Сбрасываем непрочитанные
        self._mark_read(room_id, user_id, user_type)

        return [self._serialize_message(m) for m in reversed(messages)]

    def edit_message(self, message_id: str, user_id: str, user_type: str, new_content: str) -> ChatMessage:
        """Редактировать сообщение"""
        msg = self.db.execute(select(ChatMessage).where(ChatMessage.id == message_id)).scalar_one_or_none()
        if not msg:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        sender_id = msg.sender_user_id or msg.sender_client_id
        if sender_id != user_id:
            raise HTTPException(status_code=403, detail="Можно редактировать только свои сообщения")

        msg.content = new_content
        msg.is_edited = True
        msg.edited_at = datetime.now(timezone.utc)
        self.db.commit()
        return msg

    def delete_message(self, message_id: str, user_id: str, user_type: str) -> None:
        """Мягкое удаление сообщения"""
        msg = self.db.execute(select(ChatMessage).where(ChatMessage.id == message_id)).scalar_one_or_none()
        if not msg:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        sender_id = msg.sender_user_id or msg.sender_client_id
        if sender_id != user_id:
            raise HTTPException(status_code=403, detail="Можно удалять только свои сообщения")

        msg.is_deleted = True
        msg.content = "Сообщение удалено"
        self.db.commit()

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ
    # ============================================================

    def _find_direct_room(self, a_id: str, a_type: str, b_id: str, b_type: str) -> ChatRoom | None:
        """Найти существующий direct-чат"""
        # Ищем room_type=direct где оба участника
        rooms = self.db.execute(
            select(ChatRoom).where(ChatRoom.room_type == "direct")
        ).scalars().all()

        for room in rooms:
            members = self.db.execute(select(ChatMember).where(ChatMember.room_id == room.id)).scalars().all()
            ids_in_room = set()
            for m in members:
                if m.user_id:
                    ids_in_room.add(("user", m.user_id))
                if m.client_id:
                    ids_in_room.add(("client", m.client_id))

            if (a_type, a_id) in ids_in_room and (b_type, b_id) in ids_in_room:
                return room
        return None

    def _add_member(self, room_id: str, entity_id: str, entity_type: str, role: str) -> None:
        member = ChatMember(
            id=str(uuid4()),
            room_id=room_id,
            user_id=entity_id if entity_type == "user" else None,
            client_id=entity_id if entity_type == "client" else None,
            role=role,
            unread_count=0,
        )
        self.db.add(member)

    def _add_system_message(self, room_id: str, text: str) -> None:
        msg = ChatMessage(
            id=str(uuid4()),
            room_id=room_id,
            sender_name="Система",
            message_type="system",
            content=text,
        )
        self.db.add(msg)

    def _is_member(self, room_id: str, entity_id: str, entity_type: str) -> bool:
        if entity_type == "user":
            filter_cond = and_(ChatMember.room_id == room_id, ChatMember.user_id == entity_id)
        else:
            filter_cond = and_(ChatMember.room_id == room_id, ChatMember.client_id == entity_id)

        return self.db.execute(select(ChatMember).where(filter_cond)).scalar_one_or_none() is not None

    def _mark_read(self, room_id: str, user_id: str, user_type: str) -> None:
        if user_type == "user":
            filter_cond = and_(ChatMember.room_id == room_id, ChatMember.user_id == user_id)
        else:
            filter_cond = and_(ChatMember.room_id == room_id, ChatMember.client_id == user_id)

        self.db.execute(
            ChatMember.__table__.update()
            .where(filter_cond)
            .values(unread_count=0, last_read_at=datetime.now(timezone.utc))
        )
        self.db.commit()

    @staticmethod
    def _serialize_message(msg: ChatMessage) -> dict:
        return {
            "id": msg.id,
            "room_id": msg.room_id,
            "sender_name": msg.sender_name,
            "sender_user_id": msg.sender_user_id,
            "sender_client_id": msg.sender_client_id,
            "type": msg.message_type,
            "content": msg.content,
            "reply_to_id": msg.reply_to_id,
            "attachment_url": msg.attachment_url,
            "attachment_name": msg.attachment_name,
            "is_edited": msg.is_edited,
            "is_deleted": msg.is_deleted,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
