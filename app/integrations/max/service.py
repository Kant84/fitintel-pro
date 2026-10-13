# app/integrations/max/service.py
"""MAX Messenger — push notifications by user_id or phone_number."""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://platform-api2.max.ru"


class MAXService:
    """MAX Messenger Bot API wrapper."""

    def __init__(self, bot_token: str | None = None):
        self.bot_token = bot_token or settings.MAX_BOT_TOKEN

    def _call(self, method: str, _query: dict | None = None, **params: Any) -> dict[str, Any]:
        token = self.bot_token
        if not token:
            # fallback: токен бота из настроек клуба
            try:
                from sqlalchemy import text as _t
                from app.db.session import engine as _eng
                with _eng.connect() as _c:
                    _r = _c.execute(_t("SELECT bot_token FROM max_bot_settings WHERE id=1")).first()
                    token = _r[0] if _r else None
            except Exception:
                token = None
        if not token:
            return {"ok": False, "error": "bot_token_not_configured"}
        import urllib.parse as _up
        url = "%s/%s" % (API_BASE, method)
        if _query:
            url = url + "?" + _up.urlencode({k: str(v) for k, v in _query.items() if v is not None})
        payload = {k: v for k, v in params.items() if v is not None}
        body = json.dumps(payload, ensure_ascii=False, default=str).encode()
        headers = {"Content-Type": "application/json", "Authorization": token}
        try:
            import ssl as _ssl
            try:
                import certifi as _cf
                _ctx = _ssl.create_default_context(cafile=_cf.where())
            except Exception:
                _ctx = _ssl.create_default_context()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30, context=_ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error("MAX request failed: %s", e)
            return {"ok": False, "error": str(e)}

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        elif digits.startswith("9") and len(digits) == 10:
            digits = "7" + digits
        return digits

    # ── Core messaging ────────────────────────

    def send_message(
        self,
        chat_id: int | str | None = None,
        phone_number: str | None = None,
        text: str = "",
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
        db: Any = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if chat_id:
            query["chat_id"] = chat_id
        elif phone_number:
            user_id = None
            if db is not None:
                try:
                    from sqlalchemy import text as _t
                    _digits = self._normalize_phone(phone_number)
                    _row = db.execute(_t(
                        "SELECT mb.max_user_id FROM max_bot_bindings mb "
                        "JOIN clients c ON replace(mb.client_id,'-','')=replace(c.id::text,'-','') "
                        "WHERE right(regexp_replace(c.phone,'\\D','','g'),10)=:p LIMIT 1"),
                        {"p": _digits[-10:]}).first()
                    if _row:
                        user_id = _row[0]
                except Exception as _e:
                    logger.error("MAX phone resolve failed: %s", _e)
            if user_id is None:
                return {"ok": False, "error": "phone_not_bound"}
            query["user_id"] = user_id
        else:
            return {"ok": False, "error": "chat_id or phone_number required"}
        params: dict[str, Any] = {
            "text": text,
            "format": "markdown" if str(parse_mode).lower() == "markdown" else "html",
        }
        if reply_markup:
            params["attachments"] = json.dumps(reply_markup)
        return self._call("messages", _query=query, **params)

    def send_push_by_phone(self, phone_number: str, title: str, body: str, action_url: str | None = None) -> dict[str, Any]:
        text = f"<b>{title}</b>\n\n{body}"
        keyboard = {"inline_keyboard": [[{"text": "Подробнее", "url": action_url}]]} if action_url else None
        return self.send_message(phone_number=phone_number, text=text, reply_markup=keyboard)

    def broadcast_by_phone(self, phone_numbers: list[str], text: str, **kwargs: Any) -> list[dict[str, Any]]:
        return [self.send_message(phone_number=p, text=text, **kwargs) for p in phone_numbers]

    # ── Templates ─────────────────────────────

    def send_workout_reminder(self, phone_number: str, client_name: str, workout_name: str,
                              workout_time: str, trainer_name: str | None = None) -> dict[str, Any]:
        text = f"<b>📅 Напоминание о тренировке</b>\n\nПривет, {client_name}!\n\n<b>{workout_name}</b>\n🕐 {workout_time}"
        if trainer_name:
            text += f"\n👤 Тренер: {trainer_name}"
        text += "\n\nЖдём вас! 💪"
        return self.send_message(phone_number=phone_number, text=text)

    def send_payment_due(self, phone_number: str, client_name: str, amount: float,
                         due_date: str, description: str, payment_url: str | None = None) -> dict[str, Any]:
        text = f"<b>💳 Напоминание об оплате</b>\n\n{client_name}, неоплаченный счёт:\n\n<b>Услуга:</b> {description}\n<b>Сумма:</b> {amount:,.2f} ₽\n<b>Оплатить до:</b> {due_date}"
        keyboard = {"inline_keyboard": [[{"text": "💳 Оплатить", "url": payment_url}]]} if payment_url else None
        return self.send_message(phone_number=phone_number, text=text, reply_markup=keyboard)

    def send_payment_confirmation(self, phone_number: str, client_name: str, amount: float,
                                  description: str) -> dict[str, Any]:
        text = f"<b>✅ Оплата успешна</b>\n\n{client_name}, платёж принят!\n\n<b>Сумма:</b> {amount:,.2f} ₽\n<b>Услуга:</b> {description}\n\nСпасибо! 💪"
        return self.send_message(phone_number=phone_number, text=text)

    def send_subscription_expired(self, phone_number: str, client_name: str,
                                  subscription_name: str, renewal_url: str | None = None) -> dict[str, Any]:
        text = f"<b>⏰ Абонемент истёк</b>\n\n{client_name}, срок абонемента <b>«{subscription_name}»</b> закончился.\n\nПродлите, чтобы продолжить занятия! 💪"
        keyboard = {"inline_keyboard": [[{"text": "🔄 Продлить", "url": renewal_url}]]} if renewal_url else None
        return self.send_message(phone_number=phone_number, text=text, reply_markup=keyboard)

    def send_birthday_greeting(self, phone_number: str, client_name: str,
                               club_name: str | None = None, gift_code: str | None = None) -> dict[str, Any]:
        text = f"<b>🎂 С Днём Рождения, {client_name}!</b>\n\nКоманда {club_name or settings.APP_NAME} поздравляет вас! Желаем здоровья и спортивных достижений! 💪"
        if gift_code:
            text += f"\n\n<b>🎁 Подарок:</b>\n<code>{gift_code}</code>"
        return self.send_message(phone_number=phone_number, text=text)

    def send_promotion(self, phone_number: str, title: str, description: str,
                       valid_until: str | None = None, promo_code: str | None = None,
                       discount_percent: int | None = None) -> dict[str, Any]:
        text = f"<b>🎉 {title}</b>\n\n{description}"
        if discount_percent:
            text += f"\n\n<b>Скидка: {discount_percent}%</b>"
        if promo_code:
            text += f"\n<code>Промокод: {promo_code}</code>"
        if valid_until:
            text += f"\n\n<i>Акция до {valid_until}</i>"
        return self.send_message(phone_number=phone_number, text=text)

    def send_staff_alert(self, phone_number: str, alert_type: str, message: str,
                         priority: str = "normal") -> dict[str, Any]:
        emoji = {"low": "ℹ️", "normal": "⚠️", "high": "🚨", "critical": "🔴"}
        text = f"<b>{emoji.get(priority, '⚠️')} {alert_type}</b>\n\n{message}"
        return self.send_message(phone_number=phone_number, text=text)

    def send_visit_entry(self, phone_number: str, client_name: str, entry_time: str) -> dict[str, Any]:
        text = f"<b>🚪 Добро пожаловать!</b>\n\n{client_name}, вы вошли в клуб!\n🕐 {entry_time}\n\nХорошей тренировки! 💪"
        return self.send_message(phone_number=phone_number, text=text)

    def send_visit_exit(self, phone_number: str, client_name: str, exit_time: str, duration: str) -> dict[str, Any]:
        text = f"<b>🚪 До свидания!</b>\n\n{client_name}, вы покинули клуб.\n🕐 {exit_time}\n⏱ {duration}\n\nЖдём снова! 🌟"
        return self.send_message(phone_number=phone_number, text=text)


# ── Singleton ───────────────────────────────

_max_service: MAXService | None = None


def get_max_service() -> MAXService:
    global _max_service
    if _max_service is None:
        _max_service = MAXService()
    return _max_service
