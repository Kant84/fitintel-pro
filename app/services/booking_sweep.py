"""Волна 5: свип броней — напомнить -> пин -> авто-отмена (по времени из club_params).

Правила клуба:
- за REMIND_BEFORE_HOURS: напоминание + просьба подтвердить;
- за LAST_REMIND_BEFORE_HOURS: финальный пин;
- после CONFIRM_DEADLINE_HOURS до занятия: AUTO_CANCELLED (слот освобождается),
  рейтинг НЕ падает (клиент просто не ответил).
Сообщения клиенту: прямой отправкой в MAX (токен из integration_settings,
как в messenger.py); при недоступности — запись в messenger_notifications (pending).
Запуск: поток каждые 5 мин (регистрируется при импорте, как в notifications.py),
либо POST /api/v1/services/bookings/sweep.
"""
import json
import threading
import time as _time
from datetime import datetime, timezone, timedelta

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.club_params import engine, get_param_int
from app.db.session import SessionLocal


def _max_token() -> str | None:
    try:
        with engine.begin() as c:
            row = c.execute(text("SELECT settings FROM integration_settings WHERE id='max'")).fetchone()
        if row and row[0]:
            return json.loads(row[0]).get("token") or None
    except Exception:
        pass
    return None


def _send_max(user_id: int, text_body: str) -> bool:
    tok = _max_token()
    if not tok:
        return False
    try:
        r = requests.post("https://platform-api.max.ru/messages",
                          params={"user_id": int(user_id)},
                          json={"text": text_body[:4000]},
                          headers={"Authorization": tok},
                          timeout=10)
        return r.ok
    except Exception:
        return False


def _enqueue_pending(client_id: str, body: str):
    """Фолбэк: строка в журнале мессенджера (отправится после настройки токена)."""
    try:
        with engine.begin() as c:
            c.execute(text("INSERT INTO messenger_notifications"
                           "(target_client_id, target_name, kind, body, status)"
                           " VALUES (NULL, :n, 'reminder', :b, 'pending')"),
                      {"n": str(client_id), "b": body[:4000]})
    except Exception:
        pass


def _notify(client_id: str, body: str):
    """MAX user_id из привязок; иначе — в очередь pending."""
    uid = None
    try:
        with engine.begin() as c:
            row = c.execute(text("SELECT max_user_id FROM messenger_bindings "
                                 "WHERE client_id::text=:c ORDER BY bound_at DESC LIMIT 1"),
                            {"c": str(client_id)}).fetchone()
        uid = int(row[0]) if row and row[0] else None
    except Exception:
        uid = None
    if uid and _send_max(uid, body):
        return "sent"
    _enqueue_pending(str(client_id), body)
    return "pending"


def _aware(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is None:
        return dt.astimezone()
    return dt


def sweep(now: datetime | None = None) -> dict:
    now = _aware(now) or datetime.now(timezone.utc)
    remind_h = get_param_int("REMIND_BEFORE_HOURS", 24)
    ping_h = get_param_int("LAST_REMIND_BEFORE_HOURS", 2)
    deadline_h = get_param_int("CONFIRM_DEADLINE_HOURS", 6)
    counts = {"reminded": 0, "pinged": 0, "auto_cancelled": 0}

    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT b.id, b.client_id, b.booking_date, b.status, "
            "b.reminded_at, b.pinged_at, s.name AS service_name "
            "FROM service_bookings b JOIN services s ON s.id = b.service_id "
            "WHERE b.status IN ('BOOKED','CONFIRMED')")).mappings().all()

    for r in rows:
        bd = _aware(r["booking_date"])
        if r["status"] != "BOOKED":
            continue
        if (r["reminded_at"] is None
                and timedelta(0) <= bd - now <= timedelta(hours=remind_h)):
            with engine.begin() as c:
                c.execute(text("UPDATE service_bookings SET reminded_at=:n WHERE id=:i"),
                          {"n": now, "i": str(r["id"])})
            _notify(str(r["client_id"]),
                    f"Напоминание: вы записаны на «{r['service_name']}» "
                    f"{bd:%d.%m в %H:%M}. Подтвердите запись в боте (Мои записи).")
            counts["reminded"] += 1
        elif (r["reminded_at"] is not None and r["pinged_at"] is None
              and timedelta(0) <= bd - now <= timedelta(hours=ping_h)):
            with engine.begin() as c:
                c.execute(text("UPDATE service_bookings SET pinged_at=:n WHERE id=:i"),
                          {"n": now, "i": str(r["id"])})
            _notify(str(r["client_id"]),
                    f"Через ~{ping_h} ч занятие «{r['service_name']}» ({bd:%H:%M}). "
                    f"Подтвердите запись, иначе она будет снята.")
            counts["pinged"] += 1
        if now > bd - timedelta(hours=deadline_h):
            with engine.begin() as c:
                c.execute(text("UPDATE service_bookings SET status='AUTO_CANCELLED' WHERE id=:i"),
                          {"i": str(r["id"])})
            _notify(str(r["client_id"]),
                    f"Запись на «{r['service_name']}» ({bd:%d.%m %H:%M}) снята: не подтверждена. "
                    f"Слот освобождён — запишитесь заново.")
            counts["auto_cancelled"] += 1
    return counts


# --- поток-шедулер (паттерн как в notifications.py) ---
def _sweep_loop():
    while True:
        try:
            sweep()
        except Exception:
            pass
        _time.sleep(300)


threading.Thread(target=_sweep_loop, daemon=True).start()
print("[W5] booking sweep scheduler OK (every 5 min)")