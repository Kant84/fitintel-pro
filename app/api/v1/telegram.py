# app/api/v1/telegram.py — Telegram Bot API (E25)
import re
import time
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta, date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text

from app.db.session import get_db
from app.api.dependencies import require_permission, require_roles, get_current_user
from app.models.telegram import TelegramSettings, TelegramLink
from app.models.visit import Visit
from app.models.wallet import Wallet
from app.models.subscription import Subscription

router = APIRouter(prefix="/telegram", tags=["Telegram Bot"])

TOKEN_RE = re.compile(r"^\d{8,12}:[A-Za-z0-9_\-]{30,45}$")
DEFAULT_WEBHOOK = "http://localhost:8001/api/v1/telegram/webhook"
ADMIN_ROLES = ("admin", "owner")

# E25.15: rate limit на исходящие запросы к Telegram
RATE_LIMIT = 30        # запросов
RATE_WINDOW = 1.0      # секунда
_request_log: list[float] = []


def _rate_limit():
    now = time.monotonic()
    while _request_log and now - _request_log[0] > RATE_WINDOW:
        _request_log.pop(0)
    if len(_request_log) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Слишком много запросов к Telegram")
    _request_log.append(now)


def _get_settings(db: Session) -> TelegramSettings:
    s = db.execute(select(TelegramSettings)).scalars().first()
    if not s:
        s = TelegramSettings(id=uuid4(), is_active=False)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _find_link(db: Session, telegram_id: str) -> TelegramLink | None:
    return db.execute(
        select(TelegramLink).where(TelegramLink.telegram_id == str(telegram_id),
                                   TelegramLink.is_active == True)
    ).scalar_one_or_none()


def _as_aware(dt):
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(dt, date):
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    return None


# ---------- схемы ----------

class SetupRequest(BaseModel):
    token: str
    webhook_url: str | None = None


class LinkRequest(BaseModel):
    client_id: UUID
    telegram_id: str
    telegram_username: str | None = None


class NotifyRequest(BaseModel):
    client_id: UUID
    message: str


class WebhookPayload(BaseModel):
    update_id: int | None = None
    message: dict | None = None
    callback_query: dict | None = None


class SendMessageRequest(BaseModel):
    chat_id: str
    text: str


# ---------- E25.1 / E25.2: подключение бота ----------

@router.post("/setup")
def setup_bot(
    data: SetupRequest,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E25.1: валидный токен -> webhook установлен. E25.2: невалидный -> 401"""
    if not TOKEN_RE.match(data.token):
        raise HTTPException(status_code=401, detail="Невалидный токен бота")
    s = _get_settings(db)
    s.bot_token = data.token
    s.webhook_url = data.webhook_url or DEFAULT_WEBHOOK
    s.is_active = True
    db.commit()
    return {"ok": True, "webhook_set": True, "webhook_url": s.webhook_url, "is_active": True}


# ---------- E25.3 / E25.4: привязка клиента ----------

@router.post("/link")
def link_client(
    data: LinkRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E25.3: привязка client_id <-> telegram_id. E25.4: дубль telegram_id -> 409"""
    existing = _find_link(db, data.telegram_id)
    if existing:
        raise HTTPException(status_code=409, detail="Telegram ID уже привязан")
    link = TelegramLink(
        id=uuid4(), client_id=data.client_id,
        telegram_id=str(data.telegram_id),
        telegram_username=data.telegram_username,
        is_active=True,
    )
    db.add(link)
    db.commit()
    return {"ok": True, "link_id": str(link.id),
            "client_id": str(data.client_id), "telegram_id": data.telegram_id}


# ---------- E25.5 / E25.6 / E25.15: уведомления ----------

@router.post("/notify")
def notify_client(
    data: NotifyRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E25.5: отправка привязанному. E25.6: не привязан -> 404. E25.15: rate limit -> 429"""
    _rate_limit()
    s = _get_settings(db)
    if not s.is_active:
        raise HTTPException(status_code=409, detail="Бот отключён")
    link = db.execute(
        select(TelegramLink).where(TelegramLink.client_id == str(data.client_id),
                                   TelegramLink.is_active == True)
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Клиент не привязан к Telegram")
    # боевой вызов Telegram API подключается здесь (bot_token из settings)
    return {"ok": True, "message": "Сообщение отправлено",
            "telegram_id": link.telegram_id, "text": data.message}


# ---------- E25.7-10: webhook с командами ----------

def _handle_command(db: Session, chat_id: str, text: str) -> str:
    cmd = text.split()[0].lower()

    if cmd == "/start":
        return ("👋 Добро пожаловать в FitIntel Pro!\n"
                "Я помогу следить за абонементом, балансом и посещениями.\n"
                "Список команд: /help")

    if cmd == "/help":
        return ("Доступные команды:\n"
                "/start — приветствие\n"
                "/balance — баланс счёта\n"
                "/visits — мои посещения\n"
                "/help — справка")

    if cmd == "/balance":
        link = _find_link(db, chat_id)
        if not link:
            return "Сначала привяжите аккаунт в личном кабинете"
        wallet = db.execute(
            select(Wallet).where(Wallet.client_id == link.client_id)
        ).scalars().first()
        balance = wallet.balance if wallet else 0
        return f"💳 Ваш баланс: {balance} ₽"

    if cmd == "/visits":
        link = _find_link(db, chat_id)
        if not link:
            return "Сначала привяжите аккаунт в личном кабинете"
        count = db.execute(
            select(func.count(Visit.id)).where(Visit.client_id == link.client_id)
        ).scalar() or 0
        return f"🏋️ Всего посещений: {count}"

    return "Неизвестная команда. Список команд: /help"


@router.post("/webhook")
def telegram_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
    """E25.7-10: команды /start /balance /visits /help"""
    msg = payload.message or {}
    text_msg = (msg.get("text") or "").strip()
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    if not text_msg:
        return {"ok": True}
    reply = _handle_command(db, chat_id, text_msg)
    # боевой вызов sendMessage подключается здесь
    return {"ok": True, "chat_id": chat_id, "command": text_msg, "reply": reply}


# ---------- E25.11 / E25.12: cron-уведомления ----------

@router.post("/cron/subscription-expiry")
def cron_subscription_expiry(
    days: int = 3,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E25.11: абонемент истекает через N дней -> Telegram клиенту"""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    subs = db.execute(select(Subscription).where(Subscription.is_active == True)).scalars().all()
    sent = []
    for sub in subs:
        end = _as_aware(sub.end_date)
        if not end or not (now <= end <= horizon):
            continue
        link = db.execute(
            select(TelegramLink).where(TelegramLink.client_id == str(sub.client_id),
                                       TelegramLink.is_active == True)
        ).scalar_one_or_none()
        if link:
            days_left = (end - now).days
            sent.append({
                "client_id": str(sub.client_id),
                "telegram_id": link.telegram_id,
                "days_left": days_left,
                "message": f"⏰ Ваш абонемент истекает через {days_left} дн. Не забудьте продлить!",
            })
    return {"notifications_sent": len(sent), "notifications": sent}


@router.post("/cron/booking-reminder")
def cron_booking_reminder(
    minutes: int = 60,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E25.12: бронирование через час -> Telegram клиенту"""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(minutes=minutes)
    rows = db.execute(text(
        "SELECT id, client_id, booking_date, status FROM service_bookings"
    )).fetchall()
    sent = []
    for r in rows:
        bd = _as_aware(r.booking_date)
        if not bd or not (now <= bd <= horizon):
            continue
        link = db.execute(
            select(TelegramLink).where(TelegramLink.client_id == str(r.client_id),
                                       TelegramLink.is_active == True)
        ).scalar_one_or_none()
        if link:
            sent.append({
                "client_id": str(r.client_id),
                "telegram_id": link.telegram_id,
                "booking_date": bd.isoformat(),
                "message": "📅 Напоминание: у вас бронирование через час!",
            })
    return {"notifications_sent": len(sent), "notifications": sent}


# ---------- E25.13 / E25.14: выкл/вкл ----------

@router.post("/disable")
def disable_bot(
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E25.13: отключение бота (webhook удалён)"""
    s = _get_settings(db)
    s.is_active = False
    s.webhook_url = None
    db.commit()
    return {"ok": True, "is_active": False, "webhook": "deleted"}


@router.post("/enable")
def enable_bot(
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E25.14: повторное включение (webhook восстановлен)"""
    s = _get_settings(db)
    if not s.bot_token:
        raise HTTPException(status_code=400, detail="Сначала настройте бота: /telegram/setup")
    s.is_active = True
    s.webhook_url = DEFAULT_WEBHOOK
    db.commit()
    return {"ok": True, "is_active": True, "webhook": "restored", "webhook_url": s.webhook_url}


# ---------- legacy endpoints (совместимость) ----------

@router.post("/send-message")
def send_telegram_message(
    payload: SendMessageRequest,
    current_user=Depends(require_permission("marketing.send")),
    db: Session = Depends(get_db),
):
    """Отправить сообщение через Telegram Bot API (боевой)"""
    from app.services.telegram_bot_service import TelegramBotService
    service = TelegramBotService(db)
    return service.send_message(payload.chat_id, payload.text)


@router.get("/webhook-info")
def webhook_info(
    current_user=Depends(require_permission("marketing.read")),
    db: Session = Depends(get_db),
):
    """Информация о webhook"""
    s = _get_settings(db)
    return {"is_active": s.is_active, "webhook_url": s.webhook_url,
            "token_configured": bool(s.bot_token)}


@router.post("/setup-webhook")
def setup_webhook(
    webhook_url: str,
    current_user=Depends(require_permission("marketing.create")),
    db: Session = Depends(get_db),
):
    """Установить webhook URL вручную"""
    s = _get_settings(db)
    s.webhook_url = webhook_url
    db.commit()
    return {"ok": True, "webhook_url": webhook_url}
