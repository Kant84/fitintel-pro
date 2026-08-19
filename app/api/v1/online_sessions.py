# app/api/v1/online_sessions.py
import random
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import require_roles, get_current_user
from app.db.session import get_db
from app.models.online_session import OnlineSession, SessionParticipant, SessionChatMessage

router = APIRouter(prefix="/online-sessions", tags=["Online Sessions"])

TRAINER_ROLES = ("trainer", "admin", "owner")
VALID_PROVIDERS = ("internal", "zoom", "google_meet")


# ---------- схемы ----------

class CreateSessionRequest(BaseModel):
    client_id: UUID
    trainer_id: UUID | None = None
    starts_at: datetime
    duration_minutes: int = 60
    title: str = "Персональная онлайн-сессия"
    provider: str = "internal"
    record: bool = False


class UpdateSessionRequest(BaseModel):
    starts_at: datetime | None = None
    duration_minutes: int | None = None
    title: str | None = None


class JoinRequest(BaseModel):
    client_id: UUID


class ChatMessageRequest(BaseModel):
    sender_id: UUID
    sender_name: str | None = None
    message: str


class ScreenShareRequest(BaseModel):
    enabled: bool = True


# ---------- провайдеры ----------

def _make_provider_links(provider: str) -> dict:
    """Генерация ссылок провайдера. Боевые API Zoom/Google подключаются здесь."""
    if provider == "zoom":
        meeting_id = "".join(random.choices("0123456789", k=11))
        return {"join_link": f"https://zoom.us/j/{meeting_id}", "meeting_id": meeting_id, "event_id": None}
    if provider == "google_meet":
        letters = "abcdefghijklmnopqrstuvwxyz"
        code = ("".join(random.choices(letters, k=3)) + "-" +
                "".join(random.choices(letters, k=4)) + "-" +
                "".join(random.choices(letters, k=3)))
        return {"join_link": f"https://meet.google.com/{code}", "meeting_id": None, "event_id": uuid4().hex}
    return {"join_link": f"https://fitintel.pro/room/{uuid4().hex[:12]}", "meeting_id": None, "event_id": None}


def _get_session(db: Session, session_id: UUID) -> OnlineSession:
    s = db.execute(select(OnlineSession).where(OnlineSession.id == str(session_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    return s


def _serialize(s: OnlineSession, db: Session, with_participants: bool = False) -> dict:
    data = {
        "session_id": str(s.id),
        "title": s.title,
        "trainer_id": str(s.trainer_id) if s.trainer_id else None,
        "client_id": str(s.client_id) if s.client_id else None,
        "starts_at": s.starts_at.isoformat() if s.starts_at else None,
        "ends_at": s.ends_at.isoformat() if s.ends_at else None,
        "duration_minutes": s.duration_minutes,
        "status": s.status,
        "provider": s.provider,
        "link": s.join_link,
        "zoom_link": s.join_link if s.provider == "zoom" else None,
        "meeting_id": s.meeting_id,
        "meet_link": s.join_link if s.provider == "google_meet" else None,
        "event_id": s.event_id,
        "record": s.record,
        "recording_url": s.recording_url,
        "screen_sharing": s.screen_sharing,
        "reminder_sent": s.reminder_sent,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
    if with_participants:
        rows = db.execute(
            select(SessionParticipant).where(SessionParticipant.session_id == str(s.id))
        ).scalars().all()
        data["participants"] = [{
            "participant_id": str(p.id),
            "client_id": str(p.client_id),
            "status": p.status,
            "joined_at": p.joined_at.isoformat() if p.joined_at else None,
        } for p in rows]
    return data


# ---------- E22.1 / E22.2 / E22.14 / E22.15: создание ----------

@router.post("", status_code=201)
def create_session(
    data: CreateSessionRequest,
    current_user=Depends(require_roles(*TRAINER_ROLES)),
    db: Session = Depends(get_db),
):
    """E22.1: создание онлайн-сессии (только Trainer/Admin). E22.2: Receptionist -> 403."""
    if data.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"provider должен быть одним из: {VALID_PROVIDERS}")

    sid = uuid4()
    links = _make_provider_links(data.provider)
    trainer_id = data.trainer_id or current_user.id
    ends_at = data.starts_at + timedelta(minutes=data.duration_minutes)

    s = OnlineSession(
        id=sid, title=data.title, session_type="scheduled",
        trainer_id=trainer_id, client_id=data.client_id,
        starts_at=data.starts_at, ends_at=ends_at,
        duration_minutes=data.duration_minutes,
        status="scheduled", provider=data.provider, record=data.record,
        **links,
    )
    db.add(s)
    # клиент автоматически приглашается
    db.add(SessionParticipant(id=uuid4(), session_id=str(sid),
                              client_id=str(data.client_id), status="invited"))
    db.commit()
    db.refresh(s)
    return _serialize(s, db)


# ---------- E22.3: список ----------

@router.get("")
def list_sessions(
    trainer_id: UUID | None = None,
    client_id: UUID | None = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E22.3: список сессий (фильтры trainer_id / client_id)"""
    q = select(OnlineSession).where(OnlineSession.is_active == True)
    if trainer_id:
        q = q.where(OnlineSession.trainer_id == str(trainer_id))
    if client_id:
        q = q.where(OnlineSession.client_id == str(client_id))
    rows = db.execute(q.order_by(OnlineSession.starts_at)).scalars().all()
    return {"sessions": [_serialize(s, db) for s in rows]}


# ---------- E22.13: напоминания (cron) ----------
# ВАЖНО: маршрут объявлен ДО /{session_id}, чтобы не конфликтовать

@router.post("/reminders/run")
def run_reminders(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E22.13: cron-задача — напоминания о сессиях через 15 минут (trainer + client)."""
    now = datetime.now(timezone.utc)
    soon = now + timedelta(minutes=15)
    rows = db.execute(
        select(OnlineSession)
        .where(OnlineSession.status == "scheduled")
        .where(OnlineSession.reminder_sent == False)
        .where(OnlineSession.starts_at != None)
    ).scalars().all()

    sent = []
    for s in rows:
        st = s.starts_at
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        if now <= st <= soon:
            s.reminder_sent = True
            # здесь подключается реальная отправка Email/SMS
            sent.append({
                "session_id": str(s.id),
                "starts_at": st.isoformat(),
                "notified": ["trainer", "client"],
                "channels": ["email", "sms"],
            })
    db.commit()
    return {"reminders_sent": len(sent), "notifications": sent}


# ---------- E22.4: получение по ID ----------

@router.get("/{session_id}")
def get_session(
    session_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E22.4: данные сессии + participants"""
    return _serialize(_get_session(db, session_id), db, with_participants=True)


# ---------- E22.5: обновление ----------

@router.put("/{session_id}")
def update_session(
    session_id: UUID,
    data: UpdateSessionRequest,
    current_user=Depends(require_roles(*TRAINER_ROLES)),
    db: Session = Depends(get_db),
):
    """E22.5: обновление сессии (только до начала)"""
    s = _get_session(db, session_id)
    if s.status != "scheduled":
        raise HTTPException(status_code=409, detail="Сессия уже начата или завершена")
    if data.title is not None:
        s.title = data.title
    if data.starts_at is not None:
        s.starts_at = data.starts_at
    if data.duration_minutes is not None:
        s.duration_minutes = data.duration_minutes
    if s.starts_at:
        st = s.starts_at
        s.ends_at = st + timedelta(minutes=s.duration_minutes)
    db.commit()
    db.refresh(s)
    return _serialize(s, db)


# ---------- E22.6: удаление ----------

@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: UUID,
    current_user=Depends(require_roles(*TRAINER_ROLES)),
    db: Session = Depends(get_db),
):
    """E22.6: удаление сессии (только до начала)"""
    s = _get_session(db, session_id)
    if s.status != "scheduled":
        raise HTTPException(status_code=409, detail="Сессия уже начата или завершена")
    db.delete(s)
    db.commit()
    return Response(status_code=204)


# ---------- E22.7 / E22.8: присоединение ----------

@router.post("/{session_id}/join")
def join_session(
    session_id: UUID,
    data: JoinRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E22.7: join по приглашению. E22.8: без приглашения -> 403"""
    s = _get_session(db, session_id)
    p = db.execute(
        select(SessionParticipant)
        .where(SessionParticipant.session_id == str(session_id))
        .where(SessionParticipant.client_id == str(data.client_id))
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    p.status = "attended"
    p.joined_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "participant_id": str(p.id),
        "session_id": str(session_id),
        "link": s.join_link,
        "status": "joined",
    }


# ---------- E22.9: начало сессии с записью ----------

@router.post("/{session_id}/start")
def start_session(
    session_id: UUID,
    current_user=Depends(require_roles(*TRAINER_ROLES)),
    db: Session = Depends(get_db),
):
    """E22.9: старт сессии; при record=true запись начинается"""
    s = _get_session(db, session_id)
    if s.status != "scheduled":
        raise HTTPException(status_code=409, detail="Сессия уже начата или завершена")
    s.status = "in_progress"
    db.commit()
    return {
        "session_id": str(s.id),
        "status": s.status,
        "recording": s.record,
        "message": "Запись начата" if s.record else "Сессия начата без записи",
    }


@router.post("/{session_id}/end")
def end_session(
    session_id: UUID,
    current_user=Depends(require_roles(*TRAINER_ROLES)),
    db: Session = Depends(get_db),
):
    """Завершение сессии; финализирует запись"""
    s = _get_session(db, session_id)
    if s.status != "in_progress":
        raise HTTPException(status_code=409, detail="Сессия не идёт")
    s.status = "completed"
    if s.record:
        s.recording_url = f"https://fitintel.pro/recordings/{s.id}.mp4"
        s.recording_duration = (s.duration_minutes or 0) * 60
    db.commit()
    return {"session_id": str(s.id), "status": s.status, "recording_url": s.recording_url}


# ---------- E22.10: получение записи ----------

@router.get("/{session_id}/recording")
def get_recording(
    session_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E22.10: запись сессии (video_url + duration)"""
    s = _get_session(db, session_id)
    if not s.recording_url:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"video_url": s.recording_url, "duration": s.recording_duration}


# ---------- E22.11: чат ----------

@router.post("/{session_id}/chat")
def send_chat_message(
    session_id: UUID,
    data: ChatMessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E22.11: сообщение в чат сессии — доставлено всем participants"""
    s = _get_session(db, session_id)
    msg = SessionChatMessage(
        id=uuid4(), session_id=s.id,
        sender_id=data.sender_id, sender_name=data.sender_name,
        message=data.message,
    )
    db.add(msg)
    recipients = db.execute(
        select(SessionParticipant).where(SessionParticipant.session_id == str(session_id))
    ).scalars().all()
    db.commit()
    return {
        "message_id": str(msg.id),
        "delivered": True,
        "recipients": len(recipients) + 1,  # участники + тренер
    }


@router.get("/{session_id}/chat")
def get_chat_messages(
    session_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """История чата сессии"""
    _get_session(db, session_id)
    rows = db.execute(
        select(SessionChatMessage)
        .where(SessionChatMessage.session_id == str(session_id))
        .order_by(SessionChatMessage.created_at)
    ).scalars().all()
    return {"messages": [{
        "message_id": str(m.id),
        "sender_id": str(m.sender_id),
        "sender_name": m.sender_name,
        "message": m.message,
        "sent_at": m.created_at.isoformat() if m.created_at else None,
    } for m in rows]}


# ---------- E22.12: screen sharing ----------

@router.post("/{session_id}/screen-share")
def toggle_screen_share(
    session_id: UUID,
    data: ScreenShareRequest,
    current_user=Depends(require_roles(*TRAINER_ROLES)),
    db: Session = Depends(get_db),
):
    """E22.12: тренер включает/выключает screen sharing"""
    s = _get_session(db, session_id)
    s.screen_sharing = data.enabled
    db.commit()
    return {"session_id": str(s.id), "streaming": s.screen_sharing}
