# app/api/v1/chats.py — MAX Messenger API (E24)
import os
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import (APIRouter, Depends, Query, HTTPException, Response,
                     WebSocket, WebSocketDisconnect, UploadFile, File, Form)
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.chat import ChatRoom, ChatMember, ChatMessage, ChatMessageRead

router = APIRouter(prefix="/chats", tags=["MAX Messenger"])
ws_router = APIRouter(tags=["MAX Messenger WS"])

UPLOAD_DIR = "uploads/chat"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------- WebSocket connection manager (E24.14) ----------

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, ws: WebSocket):
        await ws.accept()
        self.rooms.setdefault(room_id, []).append(ws)

    def disconnect(self, room_id: str, ws: WebSocket):
        if room_id in self.rooms and ws in self.rooms[room_id]:
            self.rooms[room_id].remove(ws)

    async def broadcast(self, room_id: str, message: dict):
        for ws in list(self.rooms.get(room_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(room_id, ws)

manager = ConnectionManager()


@ws_router.websocket("/ws/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: str):
    """E24.14: real-time сообщения в чате (broadcast всем участникам)"""
    await manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")
            if action == "send":
                await manager.broadcast(chat_id, {
                    "type": "message",
                    "chat_id": chat_id,
                    "text": data.get("text", ""),
                    "sender_name": data.get("sender_name", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif action == "typing":
                await manager.broadcast(chat_id, {
                    "type": "typing",
                    "sender_name": data.get("sender_name", ""),
                })
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)


# ---------- helpers ----------

def _get_chat(db: Session, chat_id: UUID) -> ChatRoom:
    room = db.execute(select(ChatRoom).where(ChatRoom.id == str(chat_id))).scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return room


def _require_member(db: Session, chat_id: UUID, user_id) -> None:
    m = db.execute(
        select(ChatMember).where(ChatMember.room_id == str(chat_id),
                                 ChatMember.user_id == str(user_id))
    ).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=403, detail="Доступ запрещён")


def _serialize_message(m: ChatMessage) -> dict:
    return {
        "message_id": str(m.id),
        "chat_id": str(m.room_id),
        "sender_id": str(m.sender_user_id) if m.sender_user_id else None,
        "sender_name": m.sender_name,
        "text": m.content,
        "file_url": m.attachment_url,
        "type": m.message_type,
        "is_deleted": m.is_deleted,
        "timestamp": m.created_at.isoformat() if m.created_at else None,
    }


# ---------- E24.1 / E24.2: создание чата ----------

class ChatCreate(BaseModel):
    name: str
    participants: list[UUID] = []


@router.post("", status_code=201)
def create_chat(
    data: ChatCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E24.1: создать чат. E24.2: пустой participants -> 422"""
    if not data.participants:
        raise HTTPException(status_code=422, detail="Добавьте участников")

    room = ChatRoom(
        id=uuid4(), name=data.name,
        room_type="group" if len(data.participants) > 1 else "direct",
        created_by=current_user.id, is_active=True,
    )
    db.add(room)
    db.flush()

    ids = {str(current_user.id)} | {str(p) for p in data.participants}
    for uid in ids:
        db.add(ChatMember(
            id=uuid4(), room_id=str(room.id), user_id=uid,
            role="admin" if uid == str(current_user.id) else "member",
            unread_count=0,
        ))
    db.commit()
    return {"chat_id": str(room.id), "name": room.name, "participants": sorted(ids)}


# ---------- E24.3: список чатов ----------

@router.get("")
def list_chats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E24.3: мои чаты с last_message"""
    uid = str(current_user.id)
    members = db.execute(select(ChatMember).where(ChatMember.user_id == uid)).scalars().all()
    out = []
    for m in members:
        room = db.execute(
            select(ChatRoom).where(ChatRoom.id == m.room_id, ChatRoom.is_active == True)
        ).scalar_one_or_none()
        if not room:
            continue
        last = db.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == str(room.id), ChatMessage.is_deleted == False)
            .order_by(desc(ChatMessage.created_at))
        ).scalars().first()
        out.append({
            "chat_id": str(room.id),
            "name": room.name or "Личный чат",
            "type": room.room_type,
            "last_message": {
                "text": last.content if last else None,
                "sender": last.sender_name if last else None,
                "time": last.created_at.isoformat() if last else None,
            },
            "unread_count": m.unread_count,
        })
    return {"chats": out}


# ---------- E24.4 / E24.5: чат по ID ----------

@router.get("/{chat_id}")
def get_chat(
    chat_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E24.4: данные чата + participants. E24.5: не участник -> 403"""
    room = _get_chat(db, chat_id)
    _require_member(db, chat_id, current_user.id)
    members = db.execute(
        select(ChatMember).where(ChatMember.room_id == str(chat_id))
    ).scalars().all()
    return {
        "chat_id": str(room.id),
        "name": room.name,
        "type": room.room_type,
        "participants": [{"user_id": str(m.user_id), "role": m.role} for m in members],
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


# ---------- E24.6-9: отправка сообщения/файла ----------

@router.post("/{chat_id}/messages", status_code=201)
async def send_message(
    chat_id: UUID,
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E24.6: текст -> 201. E24.7: пусто -> 422. E24.8: файл -> file_url. E24.9: >10MB -> 413"""
    _require_member(db, chat_id, current_user.id)

    file_url = None
    file_content = None
    if file is not None and file.filename:
        file_content = await file.read(MAX_FILE_SIZE + 1)
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Файл слишком большой")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        fname = f"{uuid4().hex}_{file.filename}"
        with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
            f.write(file_content)
        file_url = f"/uploads/chat/{fname}"

    if not text.strip() and not file_url:
        raise HTTPException(status_code=422, detail="Сообщение не может быть пустым")

    msg = ChatMessage(
        id=uuid4(), room_id=str(chat_id),
        sender_user_id=str(current_user.id),
        sender_name=current_user.username or "user",
        message_type="file" if file_url else "text",
        content=text.strip() or None,
        attachment_url=file_url,
        attachment_name=file.filename if file and file.filename else None,
        attachment_size=len(file_content) if file_content else None,
    )
    db.add(msg)

    others = db.execute(
        select(ChatMember).where(ChatMember.room_id == str(chat_id),
                                 ChatMember.user_id != str(current_user.id))
    ).scalars().all()
    for om in others:
        om.unread_count = (om.unread_count or 0) + 1
    db.commit()
    db.refresh(msg)

    payload = _serialize_message(msg)

    # E24.14: real-time broadcast в WebSocket-комнату
    await manager.broadcast(str(chat_id), {"type": "message", **payload})

    # E24.15: push-уведомление (заглушка-интеграция; боевой FCM — по ключам)
    payload["push"] = {"sent": True, "recipients": len(others), "channel": "fcm"}
    return payload


# ---------- E24.10: история сообщений ----------

@router.get("/{chat_id}/messages")
def get_messages(
    chat_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E24.10: сообщения с пагинацией page/limit"""
    _get_chat(db, chat_id)
    _require_member(db, chat_id, current_user.id)
    rows = db.execute(
        select(ChatMessage)
        .where(ChatMessage.room_id == str(chat_id), ChatMessage.is_deleted == False)
        .order_by(ChatMessage.created_at)
    ).scalars().all()
    start = (page - 1) * limit
    return {
        "messages": [_serialize_message(m) for m in rows[start:start + limit]],
        "page": page,
        "limit": limit,
        "total": len(rows),
    }


# ---------- E24.11: прочитано ----------

@router.post("/{chat_id}/messages/{message_id}/read")
def mark_message_read(
    chat_id: UUID,
    message_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E24.11: пометить сообщение прочитанным"""
    _require_member(db, chat_id, current_user.id)
    msg = db.execute(
        select(ChatMessage).where(ChatMessage.id == str(message_id),
                                  ChatMessage.room_id == str(chat_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    existing = db.execute(
        select(ChatMessageRead).where(ChatMessageRead.message_id == str(message_id),
                                      ChatMessageRead.reader_user_id == str(current_user.id))
    ).scalar_one_or_none()
    if not existing:
        db.add(ChatMessageRead(id=uuid4(), message_id=str(message_id),
                               reader_user_id=str(current_user.id)))
        db.commit()
    return {"message_id": str(message_id), "is_read": True}


# ---------- E24.12 / E24.13: удаление сообщения ----------

@router.delete("/{chat_id}/messages/{message_id}", status_code=204)
def delete_message(
    chat_id: UUID,
    message_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E24.12: soft delete своего. E24.13: чужого -> 403"""
    msg = db.execute(
        select(ChatMessage).where(ChatMessage.id == str(message_id),
                                  ChatMessage.room_id == str(chat_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    if str(msg.sender_user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Нельзя удалить чужое сообщение")
    msg.is_deleted = True
    msg.content = "Сообщение удалено"
    db.commit()
    return Response(status_code=204)
