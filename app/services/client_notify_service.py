"""Уведомления КЛИЕНТУ: единая точка отправки.

Приоритет каналов: MAX -> Telegram -> SMS. Канал выбирается по привязкам
клиента и настройкам клуба (notification_settings: client_notify_enabled,
cn_max, cn_telegram, cn_sms). SMS платный (SMSC) и по умолчанию ВЫКЛЮЧЕН.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.notification_service import NotificationService


def ensure_client_notify_columns(db: Session) -> None:
    stmts = [
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS client_notify_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS cn_max BOOLEAN DEFAULT TRUE",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS cn_telegram BOOLEAN DEFAULT TRUE",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS cn_sms BOOLEAN DEFAULT FALSE",
    ]
    for st in stmts:
        db.execute(text(st))
    db.commit()


class ClientNotifyService:
    def __init__(self, db: Session):
        self.db = db

    def settings(self) -> dict:
        ensure_client_notify_columns(self.db)
        row = self.db.execute(text(
            "SELECT client_notify_enabled, cn_max, cn_telegram, cn_sms "
            "FROM notification_settings LIMIT 1")).first()
        if not row:
            return {"enabled": False, "max": False, "telegram": False, "sms": False}
        return {"enabled": bool(row[0]), "max": bool(row[1]),
                "telegram": bool(row[2]), "sms": bool(row[3])}

    def resolve(self, client_id: str) -> dict:
        info = {"phone": None, "telegram_chat": None, "max_user": None}
        try:
            r = self.db.execute(text("SELECT phone FROM clients WHERE id::text=:i"),
                                {"i": str(client_id)}).first()
            if r and r[0]:
                info["phone"] = str(r[0])
        except Exception:
            pass
        try:
            r = self.db.execute(text(
                "SELECT chat_id FROM telegram_links WHERE client_id::text=:i LIMIT 1"),
                {"i": str(client_id)}).first()
            if r and r[0]:
                info["telegram_chat"] = str(r[0])
        except Exception:
            pass
        try:
            r = self.db.execute(text(
                "SELECT max_user_id FROM messenger_bindings WHERE client_id::text=:i "
                "ORDER BY created_at DESC LIMIT 1"), {"i": str(client_id)}).first()
            if r and r[0]:
                info["max_user"] = str(r[0])
        except Exception:
            pass
        if not info["max_user"]:
            try:
                r = self.db.execute(text("SELECT user_id FROM clients WHERE id::text=:i"),
                                    {"i": str(client_id)}).first()
                if r and r[0]:
                    info["max_user"] = str(r[0])
            except Exception:
                pass
        return info

    def send(self, client_id: str, event: str, message: str) -> dict:
        st = self.settings()
        res = {"ok": False, "event": event, "channel": None, "error": None, "tried": []}
        if not st.get("enabled"):
            res["error"] = "клиентские уведомления отключены настройками клуба"
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
