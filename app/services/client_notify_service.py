"""Уведомления КЛИЕНТУ: единая точка отправки.

Приоритет каналов: MAX -> Telegram -> SMS. Отдельные флажки на ТИПЫ событий:
payment (оплата), vending (вендинг), booking_reminder (запись),
subscription_expiry (абонемент). SMS платный и по умолчанию ВЫКЛЮЧЕН.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.notification_service import NotificationService

EVENT_FLAGS = {
    "payment": "cn_ev_payment",
    "vending": "cn_ev_vending",
    "booking_reminder": "cn_ev_booking",
    "subscription_expiry": "cn_ev_expiry",
    "locker_rental_expiry": "cn_ev_locker",
}

_COLUMNS = ["client_notify_enabled", "cn_max", "cn_telegram", "cn_sms",
            "cn_ev_payment", "cn_ev_vending", "cn_ev_booking", "cn_ev_expiry", "cn_ev_locker"]


_ENSURED = False


def ensure_client_notify_columns(db: Session = None) -> None:
    global _ENSURED
    if _ENSURED:
        return
    from app.db.session import engine
    with engine.begin() as c:
        for col in _COLUMNS:
            default = "FALSE" if col == "cn_sms" else "TRUE"
            c.execute(text(f"ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT {default}"))


    _ENSURED = True


class ClientNotifyService:
    def __init__(self, db: Session):
        self.db = db

    def settings(self) -> dict:
        ensure_client_notify_columns(self.db)
        cols = ", ".join(_COLUMNS)
        row = self.db.execute(text(f"SELECT {cols} FROM notification_settings LIMIT 1")).first()
        if not row:
            return {"enabled": False, "max": False, "telegram": False, "sms": False,
                    "events": {k: False for k in EVENT_FLAGS}}
        d = dict(zip(_COLUMNS, row))
        return {
            "enabled": bool(d["client_notify_enabled"]),
            "max": bool(d["cn_max"]),
            "telegram": bool(d["cn_telegram"]),
            "sms": bool(d["cn_sms"]),
            "events": {ev: bool(d[col]) for ev, col in EVENT_FLAGS.items()},
        }

    def resolve(self, client_id: str) -> dict:
        info = {"phone": None, "telegram_chat": None, "max_user": None}
        for key, sql in (
            ("phone", "SELECT phone FROM clients WHERE id::text=:i"),
            ("telegram_chat", "SELECT chat_id FROM telegram_links WHERE client_id::text=:i LIMIT 1"),
            ("max_user", "SELECT max_user_id FROM messenger_bindings WHERE client_id::text=:i ORDER BY length(max_user_id) ASC LIMIT 1"),
        ):
            try:
                r = self.db.execute(text(sql), {"i": str(client_id)}).first()
                if r and r[0]:
                    info[key] = str(r[0])
            except Exception:
                self.db.rollback()
        if not info["max_user"]:
            try:
                r = self.db.execute(text("SELECT user_id FROM clients WHERE id::text=:i"),
                                    {"i": str(client_id)}).first()
                if r and r[0]:
                    info["max_user"] = str(r[0])
            except Exception:
                self.db.rollback()
        return info

    def send(self, client_id: str, event: str, message: str) -> dict:
        st = self.settings()
        res = {"ok": False, "event": event, "channel": None, "error": None, "tried": []}
        if not st.get("enabled"):
            res["error"] = "клиентские уведомления отключены настройками клуба"
            return res
        if event in EVENT_FLAGS and not st.get("events", {}).get(event, True):
            res["error"] = f"событие '{event}' отключено настройками клуба"
            return res
        info = self.resolve(client_id)
        ns = NotificationService(self.db)
        plan = []
        if st.get("max") and info["max_user"]:
            plan.append(("max", lambda: ns.send_max_message(info["max_user"], message)))
        if st.get("telegram") and info["telegram_chat"]:
            plan.append(("telegram", lambda: ns.send_telegram(info["telegram_chat"], message)))
        if st.get("sms") and info["phone"]:
            plan.append(("sms", lambda: ns.send_sms(info["phone"], message)))
        if not plan:
            res["error"] = ("нет доступных каналов: у клиента нет привязок "
                            "(MAX-пользователь / Telegram / телефон) или все каналы отключены")
            return res
        for channel, fn in plan:
            try:
                ok = bool(fn())
                res["tried"].append({"channel": channel, "ok": ok})
                if ok:
                    res.update(ok=True, channel=channel)
                    return res
            except Exception as e:
                res["tried"].append({"channel": channel, "ok": False, "error": str(e)[:120]})
        res["error"] = "все доступные каналы вернули неуспех"
        return res

