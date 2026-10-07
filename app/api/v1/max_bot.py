"""MAX Messenger бот (B6 + Волна 5).

Волна 5:
- /qr выдаётся по ОСНОВАНИЯМ входа (entry_policy: абонемент ИЛИ оплаченное занятие
  в окне ±QR_ACCESS_WINDOW_HOURS), TTL и пауза обновления — из club_params;
- cooldown на повторный /qr (QR_REFRESH_COOLDOWN_SECONDS);
- /bonuses — баланс кошелька + уровень геймификации (заглушка «скоро»);
- webhook пытается доставить ответ в MAX напрямую (если задан токен бота).
"""
import hashlib
import hmac as hmac_mod
import json
import time
import uuid
import base64 as _b64
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()

try:
    from app.api.v1.dynamic_qr import generate_qr_payload, QR_TTL
except Exception:
    def generate_qr_payload(client_id, expires, ttl):
        raise RuntimeError("dynamic_qr not available")
    QR_TTL = 120
from app.core.config import settings

# импорты club_params — ленивые (внутри функций), см. ниже

# --- QR refresh cooldown (in-memory) ---
_last_qr: dict[str, float] = {}


def _get_settings(db: Session):
    row = db.execute(sql_text(
        "SELECT bot_token, webhook_secret FROM max_bot_settings WHERE id=1")).first()
    if not row:
        return {"bot_token": settings.MAX_BOT_TOKEN, "webhook_secret": ""}
    return {"bot_token": row[0] or settings.MAX_BOT_TOKEN,
            "webhook_secret": row[1] or ""}


class MaxSettingsIn(BaseModel):
    bot_token: Optional[str] = None
    webhook_secret: Optional[str] = None


@router.get("/max-bot/settings")
def get_bot_settings(db: Session = Depends(get_db)):
    s = _get_settings(db)
    return {"bot_token_set": bool(s["bot_token"]),
            "webhook_secret_set": bool(s["webhook_secret"])}


@router.post("/max-bot/settings")
def set_bot_settings(body: MaxSettingsIn, db: Session = Depends(get_db)):
    if body.bot_token is not None:
        db.execute(sql_text(
            "INSERT INTO max_bot_settings (id, bot_token) VALUES (1, :t) "
            "ON CONFLICT (id) DO UPDATE SET bot_token = :t"), {"t": body.bot_token})
    if body.webhook_secret is not None:
        db.execute(sql_text(
            "INSERT INTO max_bot_settings (id, webhook_secret) VALUES (1, :s) "
            "ON CONFLICT (id) DO UPDATE SET webhook_secret = :s"), {"s": body.webhook_secret})
    db.commit()
    return {"ok": True}


def _ensure_bot_tables(db: Session):
    db.execute(sql_text("""
        CREATE TABLE IF NOT EXISTS max_bot_settings (
            id INT PRIMARY KEY,
            bot_token TEXT,
            webhook_secret TEXT,
            updated_at TIMESTAMP DEFAULT NOW())"""))
    db.execute(sql_text("""
        CREATE TABLE IF NOT EXISTS max_bot_log (
            id BIGSERIAL PRIMARY KEY,
            max_user_id BIGINT,
            command TEXT,
            payload TEXT,
            reply TEXT,
            created_at TIMESTAMP DEFAULT NOW())"""))
    db.commit()


def _log(db: Session, max_user_id, command, payload, reply):
    try:
        db.execute(sql_text(
            "INSERT INTO max_bot_log (max_user_id, command, payload, reply) "
            "VALUES (:u, :c, :p, :r)"),
            {"u": max_user_id, "c": command,
             "p": json.dumps(payload, ensure_ascii=False)[:500],
             "r": json.dumps(reply, ensure_ascii=False)[:500]})
        db.commit()
    except Exception:
        db.rollback()


def _verify_secret(db: Session, secret: str) -> bool:
    if not secret:
        return False
    s = _get_settings(db)
    expected = s["webhook_secret"]
    if not expected:
        return False
    return hmac_mod.compare_digest(secret.encode(), expected.encode())


def _find_client(db: Session, max_user_id: int):
    row = db.execute(sql_text("""
        SELECT c.id, c.first_name, c.last_name, c.phone
        FROM clients c
        JOIN messenger_bindings mb ON mb.client_id::text = c.id::text
        WHERE mb.max_user_id = :u
        ORDER BY mb.bound_at DESC LIMIT 1"""), {"u": max_user_id}).first()
    return row


def _wallet_balance(db: Session, client_id) -> Optional[float]:
    try:
        row = db.execute(sql_text(
            "SELECT balance FROM wallets WHERE client_id=:c"), {"c": str(client_id)}).first()
        return float(row[0]) if row else None
    except Exception:
        return None


def _gamification(db: Session, client_id):
    try:
        row = db.execute(sql_text(
            "SELECT level, xp FROM gamification_levels WHERE client_id=:c"),
            {"c": str(client_id)}).first()
        return row
    except Exception:
        return None


def _handle_command(db: Session, max_user_id: int, text: str) -> dict:
    from app.api.v1.club_params import get_label
    cmd = (text or "").strip().lower()
    _ensure_bot_tables(db)

    if cmd in ("/start", "start", "старт", "привет"):
        return {"reply": "Привет! Я бот фитнес-клуба.\n"
                         "Команды: /qr — пропуск, /balance — баланс, "
                         "/visits — посещения, /abonement — абонемент, "
                         "/bonuses — бонусы, /help — помощь."}
    if cmd in ("/help", "помощь"):
        return {"reply": "/qr — QR-код для входа\n"
                         "/balance — баланс\n"
                         "/visits — мои посещения\n"
                         "/abonement — мой абонемент\n"
                         "/bonuses — бонусы"}

    if cmd in ("/qr", "qr", "вход"):
        return _qr_entry_reply(db, max_user_id)

    if cmd in ("/balance", "баланс", "баланс"):
        row = _find_client(db, max_user_id)
        if not row:
            return {"reply": "Привяжите карточку клиента на ресепшене для просмотра баланса."}
        bal = _wallet_balance(db, row[0])
        if bal is None:
            return {"reply": "Кошелёк не найден."}
        return {"reply": f"💰 Ваш баланс: {bal:.2f} ₽"}

    if cmd in ("/visits", "посещения"):
        row = _find_client(db, max_user_id)
        if not row:
            return {"reply": "Привяжите карточку клиента на ресепшене."}
        visits = db.execute(sql_text("""
            SELECT entry_time, access_method FROM visits
            WHERE client_id = :c ORDER BY entry_time DESC LIMIT 5"""),
            {"c": str(row[0])}).fetchall()
        if not visits:
            return {"reply": "Посещений пока нет."}
        lines = ["Последние посещения:"]
        for v in visits:
            dt = v[0]
            if isinstance(dt, str):
                dt_str = dt[:16]
            else:
                dt_str = dt.strftime("%d.%m.%Y %H:%M") if dt else "—"
            lines.append(f"  {dt_str} ({v[1] or 'QR'})")
        return {"reply": "\n".join(lines)}

    if cmd in ("/abonement", "абонемент"):
        row = _find_client(db, max_user_id)
        if not row:
            return {"reply": "Привяжите карточку клиента на ресепшене."}
        sub = db.execute(sql_text("""
            SELECT s.id, s.status, s.end_date, t.name, t.visit_limit, s.visits_used
            FROM subscriptions s
            JOIN tariffs t ON t.id = s.tariff_id
            WHERE s.client_id = :c AND s.is_active = TRUE
            ORDER BY s.created_at DESC LIMIT 1"""), {"c": str(row[0])}).first()
        if not sub:
            return {"reply": "Активный абонемент не найден."}
        status_map = {"ACTIVE": "активен", "FROZEN": "заморожен", "EXPIRED": "истёк"}
        left = "∞" if not sub[4] else str(sub[4] - (sub[5] or 0))
        return {"reply": f"Абонемент «{sub[3]}»: {status_map.get(sub[1], sub[1])}.\n"
                         f"Действует до: {sub[2]}. Осталось визитов: {left}"}

    if cmd in ("/bonuses", "бонусы"):
        row = _find_client(db, max_user_id)
        if not row:
            return {"reply": "Привяжите карточку клиента на ресепшене."}
        bal = _wallet_balance(db, row[0])
        gam = _gamification(db, row[0])
        parts = []
        if gam:
            parts.append(f"⭐ Уровень {gam[0]} ({gam[1]} XP)")
        if bal is not None:
            parts.append(f"💰 Баланс: {bal:.2f} ₽")
        parts.append(get_label("TXT.BONUSES.SOON", "Программа бонусов скоро появится!"))
        return {"reply": "\n".join(parts)}

    if cmd in ("/link", "привязать"):
        return {"reply": "Для привязки скажите ID на ресепшене или продиктуйте номер телефона администратору."}

    return {"reply": "Неизвестная команда. /help — список команд."}


def _qr_entry_reply(db: Session, max_user_id: int) -> dict:
    """Волна 5: QR по основаниям входа (абонемент ИЛИ оплаченное занятие)."""
    from app.services.entry_policy import entry_reasons
    from app.api.v1.club_params import get_param_int, get_label

    row = _find_client(db, max_user_id)
    if not row:
        return {"reply": "Привяжите карточку клиента на ресепшене для получения QR-кода."}

    cooldown = get_param_int("QR_REFRESH_COOLDOWN_SECONDS", 20)
    last = _last_qr.get(str(max_user_id), 0)
    if time.time() - last < cooldown:
        return {"reply": f"QR обновляется не чаще раза в {cooldown} сек. Подождите."}

    reasons = entry_reasons(db, str(row[0]))
    if not reasons:
        return {"reply": get_label("TXT.QR.NO_ACCESS")}

    _last_qr[str(max_user_id)] = time.time()
    ttl_minutes = get_param_int("QR_TTL_MINUTES", 2)
    expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    payload, signature, _ = generate_qr_payload(str(row[0]), expires, ttl_minutes * 60)

    # B6: запись в DynamicQRCode — турникет проверяет одноразовость по записи (uses_count/max_uses)
    from app.models.dynamic_qr import DynamicQRCode
    db.add(DynamicQRCode(client_id=row[0], qr_payload=payload, signature=signature,
                         expires_at=expires, is_used=False, max_uses=1))
    db.commit()

    lines = [get_label("TXT.QR.TITLE", "✅ Основание для входа")]
    lines += [f"• {r}" for r in reasons]
    lines.append(f"\nQR одноразовый, действует {ttl_minutes} мин.")
    return {"reply": "\n".join(lines), "qr_payload": payload}


# ========== webhook ==========

def _try_send_reply(db: Session, max_user_id: int, reply: dict):
    """Лучшая попытка доставить ответ в MAX (не падаем в тестах/без токена)."""
    text_body = reply.get("reply")
    if not text_body:
        return
    s = _get_settings(db)
    if not s.get("bot_token"):
        return
    try:
        requests.post("https://platform-api.max.ru/messages",
                      params={"user_id": int(max_user_id)},
                      json={"text": text_body[:4000]},
                      headers={"Authorization": s["bot_token"]},
                      timeout=5)
    except Exception:
        pass


@router.post("/max-bot/webhook")
async def max_bot_webhook(request: Request,
                          db: Session = Depends(get_db),
                          x_max_bot_secret: str = Header(default="")):
    _ensure_bot_tables(db)
    if not _verify_secret(db, x_max_bot_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    update = body.get("update", body)
    msg = (update.get("message") or update.get("callback_query") or {})
    sender = msg.get("sender") or msg.get("from") or {}
    max_user_id = sender.get("user_id")
    text = msg.get("text") or msg.get("data") or ""

    if not max_user_id:
        return {"ok": True}

    reply = _handle_command(db, int(max_user_id), str(text))
    _log(db, int(max_user_id), str(text)[:50], body, reply)

    # Волна 5: доставляем ответ клиенту напрямую (в тестах токена нет — молча пропускаем)
    _try_send_reply(db, int(max_user_id), reply)

    # Фолбэк (старый боевой вызов):
    # s = _get_settings(db)
    # requests.post("https://platform-api.max.ru/messages",
    #               params={"user_id": max_user_id},
    #               json=reply, headers={"Authorization": s["bot_token"]}, timeout=5)
    return {"ok": True, "reply": reply}


# ========== cron: абонементы + записи (B6, без изменений) ==========

@router.post("/max-bot/cron/notify-expiring")
def cron_notify_expiring(db: Session = Depends(get_db)):
    _ensure_bot_tables(db)
    rows = db.execute(sql_text("""
        SELECT c.id, c.first_name, s.end_date, t.name AS tariff_name
        FROM clients c
        JOIN subscriptions s ON s.client_id = c.id
        JOIN tariffs t ON t.id = s.tariff_id
        WHERE s.status = 'ACTIVE' AND s.is_active = TRUE
          AND s.end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '3 days'
        LIMIT 50""")).fetchall()
    notifications = []
    for r in rows:
        notifications.append({
            "client_id": str(r[0]),
            "client_name": r[1],
            "message": f"Здравствуйте, {r[1]}! Ваш абонемент «{r[3]}» истекает {r[2]}. "
                       f"Не забудьте продлить!",
        })
    return {"notifications": notifications, "count": len(notifications)}


@router.post("/max-bot/cron/notify-bookings")
def cron_notify_bookings(db: Session = Depends(get_db)):
    _ensure_bot_tables(db)
    rows = db.execute(sql_text("""
        SELECT sb.client_id, c.first_name, s.name AS service_name, sb.booking_date
        FROM service_bookings sb
        JOIN clients c ON c.id = sb.client_id
        JOIN services s ON s.id = sb.service_id
        WHERE sb.status = 'BOOKED'
          AND sb.booking_date BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
        LIMIT 50""")).fetchall()
    notifications = []
    for r in rows:
        bd = r[3]
        bd_str = bd.strftime("%d.%m.%Y %H:%M") if hasattr(bd, "strftime") else str(bd)[:16]
        notifications.append({
            "client_id": str(r[0]),
            "client_name": r[1],
            "message": f"Напоминание: завтра запись на «{r[2]}» ({bd_str}).",
        })
    return {"notifications": notifications, "count": len(notifications)}