# app/tasks/notifications_max.py
"""Celery tasks for MAX Messenger push notifications."""

from __future__ import annotations

import logging
from typing import Any

from celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_verification_code(self, phone_number: str = "", code: str = "") -> dict[str, Any]:
    """Send phone verification code via MAX push notification."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        text = (
            f"<b>🔐 Код подтверждения</b>\n\n"
            f"Ваш код для регистрации:\n"
            f"<code>{code}</code>\n\n"
            f"Никому не сообщайте. Действителен 10 минут."
        )
        result = svc.send_message(phone_number=phone_number, text=text)
        logger.info("MAX verify code to %s: %s", phone_number, result.get("ok"))
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_push(self, phone_number: str = "", title: str = "", body: str = "") -> dict[str, Any]:
    """Send push notification via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_push_by_phone(phone_number=phone_number, title=title, body=body)
        logger.info("MAX push to %s: %s", phone_number, result.get("ok"))
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_workout_reminder(self, phone_number: str = "", client_name: str = "",
                               workout_name: str = "", workout_time: str = "",
                               trainer_name: str | None = None) -> dict[str, Any]:
    """Send workout reminder via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_workout_reminder(
            phone_number=phone_number, client_name=client_name,
            workout_name=workout_name, workout_time=workout_time, trainer_name=trainer_name,
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_payment_due(self, phone_number: str = "", client_name: str = "", amount: float = 0.0,
                         due_date: str = "", description: str = "", payment_url: str | None = None) -> dict[str, Any]:
    """Send payment due reminder via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_payment_due(
            phone_number=phone_number, client_name=client_name,
            amount=amount, due_date=due_date, description=description, payment_url=payment_url,
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_payment_confirmation(self, phone_number: str = "", client_name: str = "",
                                  amount: float = 0.0, description: str = "") -> dict[str, Any]:
    """Send payment confirmation via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_payment_confirmation(
            phone_number=phone_number, client_name=client_name, amount=amount, description=description,
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_subscription_expired(self, phone_number: str = "", client_name: str = "",
                                  subscription_name: str = "", renewal_url: str | None = None) -> dict[str, Any]:
    """Send subscription expiry via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_subscription_expired(
            phone_number=phone_number, client_name=client_name,
            subscription_name=subscription_name, renewal_url=renewal_url,
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=2, default_retry_delay=60)
def max_send_birthday_greeting(self, phone_number: str = "", client_name: str = "",
                                club_name: str | None = None, gift_code: str | None = None) -> dict[str, Any]:
    """Send birthday greeting via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_birthday_greeting(
            phone_number=phone_number, client_name=client_name, club_name=club_name, gift_code=gift_code,
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=2, default_retry_delay=60)
def max_send_promotion(self, phone_number: str = "", title: str = "", description: str = "",
                       valid_until: str | None = None, promo_code: str | None = None,
                       discount_percent: int | None = None) -> dict[str, Any]:
    """Send promotional offer via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_promotion(
            phone_number=phone_number, title=title, description=description,
            valid_until=valid_until, promo_code=promo_code, discount_percent=discount_percent,
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_staff_alert(self, phone_number: str = "", alert_type: str = "", message: str = "",
                         priority: str = "normal") -> dict[str, Any]:
    """Send staff alert via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_staff_alert(
            phone_number=phone_number, alert_type=alert_type, message=message, priority=priority,
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_visit_entry(self, phone_number: str = "", client_name: str = "", entry_time: str = "") -> dict[str, Any]:
    """Send visit entry via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_visit_entry(phone_number=phone_number, client_name=client_name, entry_time=entry_time)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def max_send_visit_exit(self, phone_number: str = "", client_name: str = "", exit_time: str = "",
                        duration: str = "") -> dict[str, Any]:
    """Send visit exit via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        result = svc.send_visit_exit(phone_number=phone_number, client_name=client_name, exit_time=exit_time, duration=duration)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def max_broadcast_by_phone(self, phone_numbers: list[str] = None, title: str = "", body: str = "") -> list[dict[str, Any]]:
    """Broadcast push to multiple phone numbers via MAX."""
    try:
        from app.integrations.max import get_max_service
        svc = get_max_service()
        text = f"<b>{title}</b>\n\n{body}" if title else body
        results = svc.broadcast_by_phone(phone_numbers=phone_numbers or [], text=text)
        logger.info("MAX broadcast to %d phones", len(phone_numbers or []))
        return results
    except Exception as exc:
        raise self.retry(exc=exc)
