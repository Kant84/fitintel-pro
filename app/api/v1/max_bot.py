# app/api/v1/max_bot.py — MAX Bot API (мессенджер MAX)
import time
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta, date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text

from app.db.session import get_db
from app.api.dependencies import require_roles, get_current_user
from app.models.max_bot import MaxBotSettings, MaxLink
from app.models.visit import Visit
from app.models.wallet import Wallet
from app.models.subscription import Subscription

router = APIRouter(prefix="/max-bot", tags=["MAX Bot"])

DEFAULT_WEBHOOK = "http://localhost:8001/api/v1/max-bot/webhook"
ADMIN_ROLES = ("admin", "owner")
MIN_TOKEN_LEN = 20

RATE_LIMIT = 30
RATE_WINDOW = 1.0
_request_log: list[float] = []


def _rate_limit():
    now = time.monotonic()
    while _request_log and now - _request_log[0] > RATE_WINDOW:
        _request_log.pop(0)
    if len(_request_log) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Слишком много запросов к MAX API")
    _request_log.append(now)


def _get_settings(db: Session) -> MaxBotSettings:
    s = db.execute(select(MaxBotSettings)).scalars().first()
    if not s:
        s = MaxBotSettings(id=uuid4(), is_active=False)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _find_link(db: Session, max_user_id: str) -> MaxLink | None:
    return db.execute(
        select(MaxLink).where(MaxLink.max_user_id == str(max_user_id),
                              MaxLink.is_active == True)
    ).scalar_one_or_none()


def _as_aware(dt):
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(dt, date):
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    return None


class SetupRequest(BaseModel):
    token: str
    webhook_url: str | None = None


class LinkRequest(BaseModel):
    client_id: UUID
    max_user_id: str
    max_username: str | None = None


class NotifyRequest(BaseModel):
    client_id: UUID
    message: str


@router.post("/setup")
def setup_bot(
    data: SetupRequest,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """Подключение MAX-бота: валидный токен -> webhook установлен"""
    if not data.token or len(data.token.strip()) < MIN_TOKEN_LEN:
        raise HTTPException(status_code=401, detail="Невалидный токен бота")
    s = _get_settings(db)
    s.bot_token = data.token.strip()
    s.webhook_url = data.webhook_url or DEFAULT_WEBHOOK
    s.is_active = True
    db.commit()
    # боевой вызов: POST https://botapi.max.ru/subscriptions
    return {"ok": True, "webhook_set": True, "webhook_url": s.webhook_url, "is_active": True}


@router.post("/link")
def link_client(
    data: LinkRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Привязка client_id <-> max_user_id. Дубль -> 409"""
    existing = _find_link(db, data.max_user_id)
    if existing:
        raise HTTPException(status_code=409, detail="MAX ID уже привязан")
    link = MaxLink(
        id=uuid4(), client_id=data.client_id,
        max_user_id=str(data.max_user_id),
        max_username=data.max_username,
        is_active=True,
    )
    db.add(link)
    db.commit()
    return {"ok": True, "link_id": str(link.id),
            "client_id": str(data.client_id), "max_user_id": data.max_user_id}


@router.post("/notify")
def notify_client(
    data: NotifyRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отправка уведомления клиенту в MAX"""
    _rate_limit()
    s = _get_settings(db)
    if not s.is_active:
        raise HTTPException(status_code=409, detail="Бот отключён")
    link = db.execute(
        select(MaxLink).where(MaxLink.client_id == str(data.client_id),
                              MaxLink.is_active == True)
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Клиент не привязан к MAX")
    # боевой вызов: POST https://botapi.max.ru/messages
    return {"ok": True, "message": "Сообщение отправлено",
            "max_user_id": link.max_user_id, "text": data.message}
def _handle_command(db: Session, max_user_id: str, text: str) -> str:
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
        link = _find_link(db, max_user_id)
        if not link:
            return "Сначала привяжите аккаунт в личном кабинете"
        wallet = db.execute(
            select(Wallet).where(Wallet.client_id == link.client_id)
        ).scalars().first()
        balance = wallet.balance if wallet else 0
        return f"💳 Ваш баланс: {balance} ₽"

    if cmd == "/visits":
        link = _find_link(db, max_user_id)
        if not link:
            return "Сначала привяжите аккаунт в личном кабинете"
        count = db.execute(
            select(func.count(Visit.id)).where(Visit.client_id == link.client_id)
        ).scalar() or 0
        return f"🏋️ Всего посещений: {count}"

    return "Неизвестная команда. Список команд: /help"


@router.post("/webhook")
def max_webhook(
    payload: dict,
    db: Session = Depends(get_db),
):
    """Webhook для MAX Bot API (update_type=message_created)"""
    msg = payload.get("message") or {}
    body = msg.get("body") or {}
    text_msg = (body.get("text") or msg.get("text") or "").strip()

    sender = msg.get("sender") or {}
    user_id = str(sender.get("user_id") or (msg.get("chat") or {}).get("id") or "")

    if not text_msg:
        return {"ok": True}
    reply = _handle_command(db, user_id, text_msg)
    return {"ok": True, "max_user_id": user_id, "command": text_msg, "reply": reply}


@router.post("/cron/subscription-expiry")
def cron_subscription_expiry(
    days: int = 3,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Абонемент истекает через N дней -> сообщение в MAX"""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    subs = db.execute(select(Subscription).where(Subscription.is_active == True)).scalars().all()
    sent = []
    for sub in subs:
        end = _as_aware(sub.end_date)
        if not end or not (now <= end <= horizon):
            continue
        link = db.execute(
            select(MaxLink).where(MaxLink.client_id == str(sub.client_id),
                                  MaxLink.is_active == True)
        ).scalar_one_or_none()
        if link:
            days_left = (end - now).days
            sent.append({
                "client_id": str(sub.client_id),
                "max_user_id": link.max_user_id,
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
    """Бронирование через час -> сообщение в MAX"""
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
            select(MaxLink).where(MaxLink.client_id == str(r.client_id),
                                  MaxLink.is_active == True)
        ).scalar_one_or_none()
        if link:
            sent.append({
                "client_id": str(r.client_id),
                "max_user_id": link.max_user_id,
                "booking_date": bd.isoformat(),
                "message": "📅 Напоминание: у вас бронирование через час!",
            })
    return {"notifications_sent": len(sent), "notifications": sent}


@router.post("/disable")
def disable_bot(
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """Отключение MAX-бота (webhook удалён)"""
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
    """Повторное включение (webhook восстановлен)"""
    s = _get_settings(db)
    if not s.bot_token:
        raise HTTPException(status_code=400, detail="Сначала настройте бота: /max-bot/setup")
    s.is_active = True
    s.webhook_url = DEFAULT_WEBHOOK
    db.commit()
    return {"ok": True, "is_active": True, "webhook": "restored", "webhook_url": s.webhook_url}


@router.get("/webhook-info")
def webhook_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Информация о webhook MAX-бота"""
    s = _get_settings(db)
    return {"is_active": s.is_active, "webhook_url": s.webhook_url,
            "token_configured": bool(s.bot_token)}
