# app/api/v1/chat.py
"""
MAX Messenger — API чата.
REST + WebSocket для real-time messaging.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.api.dependencies import get_current_user, require_permission
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["MAX Messenger"])


# ============================================================
# WEBSOCKET — REAL-TIME
# ============================================================

@router.websocket("/ws/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: str):
    """WebSocket для real-time сообщений в комнате"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")

            if action == "send":
                # {action: "send", content: "...", sender_id: "...", sender_type: "user", sender_name: "..."}
                await websocket.send_json({
                    "type": "message",
                    "room_id": room_id,
                    "content": data.get("content", ""),
                    "sender_name": data.get("sender_name", ""),
                    "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                })
            elif action == "typing":
                await websocket.send_json({
                    "type": "typing",
                    "sender_name": data.get("sender_name", ""),
                })
    except WebSocketDisconnect:
        pass


# ============================================================
# СХЕМЫ
# ============================================================

class CreateDirectChat(BaseModel):
    target_id: str
    target_type: str  # user | client


class CreateGroupChat(BaseModel):
    name: str
    description: Optional[str] = ""
    members: list[dict]  # [{"id": str, "type": str}]


class SendMessage(BaseModel):
    content: str
    message_type: str = "text"
    reply_to_id: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None


class EditMessage(BaseModel):
    content: str


# ============================================================
# КОМНАТЫ
# ============================================================

def get_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


@router.get("/rooms")
def list_my_rooms(
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """Мои чаты"""
    return {"rooms": service.list_user_rooms(str(current_user.id), "user")}


@router.post("/rooms/direct")
def create_direct_chat(
    payload: CreateDirectChat,
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """Создать личный чат"""
    room = service.create_direct_chat(
        str(current_user.id), "user",
        payload.target_id, payload.target_type
    )
    return {"room_id": room.id, "type": "direct"}


@router.post("/rooms/group")
def create_group_chat(
    payload: CreateGroupChat,
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """Создать групповой чат"""
    room = service.create_group_room(
        payload.name,
        str(current_user.id), "user",
        payload.members,
        payload.description,
    )
    return {"room_id": room.id, "type": "group", "name": room.name}


@router.get("/rooms/{room_id}")
def get_room(
    room_id: str,
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """Информация о чате"""
    room = service.get_room(room_id)
    return {
        "id": room.id,
        "name": room.name,
        "type": room.room_type,
        "description": room.description,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


# ============================================================
# СООБЩЕНИЯ
# ============================================================

@router.get("/rooms/{room_id}/messages")
def get_messages(
    room_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """История сообщений"""
    messages = service.get_messages(room_id, str(current_user.id), "user", limit, before_id)
    return {"messages": messages}


@router.post("/rooms/{room_id}/messages")
def send_message(
    room_id: str,
    payload: SendMessage,
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """Отправить сообщение"""
    msg = service.send_message(
        room_id=room_id,
        sender_id=str(current_user.id),
        sender_type="user",
        sender_name=f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.username,
        content=payload.content,
        message_type=payload.message_type,
        reply_to_id=payload.reply_to_id,
        attachment_url=payload.attachment_url,
        attachment_name=payload.attachment_name,
    )
    return service._serialize_message(msg)


@router.patch("/messages/{message_id}")
def edit_message(
    message_id: str,
    payload: EditMessage,
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """Редактировать сообщение"""
    msg = service.edit_message(message_id, str(current_user.id), "user", payload.content)
    return service._serialize_message(msg)


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: str,
    current_user=Depends(get_current_user),
    service: ChatService = Depends(get_service),
):
    """Удалить сообщение"""
    service.delete_message(message_id, str(current_user.id), "user")
    return {"status": "deleted"}
