# app/integrations/max/verification.py
"""
Phone verification service via MAX Messenger push notifications.

Flow:
1. Client enters phone number during registration
2. System generates 6-digit code, sends via MAX push
3. Client enters code in app
4. System verifies code from Redis
"""

from __future__ import annotations

import ast
import logging
import random
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class PhoneVerificationService:
    """Phone number verification via MAX push notifications."""

    CODE_LENGTH = 6
    CODE_TTL_SECONDS = 600  # 10 minutes
    MAX_ATTEMPTS = 3
    COOLDOWN_SECONDS = 60   # 1 minute between resends
    REDIS_KEY_PREFIX = "phone_verify"

    def __init__(self, redis_client=None):
        self._redis = redis_client

    @property
    def redis(self):
        if self._redis is None:
            import redis as redis_lib
            self._redis = redis_lib.from_url(settings.REDIS_URL)
        return self._redis

    def _key(self, phone: str) -> str:
        return f"{self.REDIS_KEY_PREFIX}:{phone}"

    def _normalize_phone(self, phone: str) -> str:
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        elif digits.startswith("9") and len(digits) == 10:
            digits = "7" + digits
        return digits

    def _generate_code(self) -> str:
        return str(random.randint(100000, 999999))

    def send_code(self, phone_number: str, send_via: str = "max") -> dict[str, Any]:
        """Generate and send verification code."""
        phone = self._normalize_phone(phone_number)
        key = self._key(phone)

        existing_ttl = self.redis.ttl(key)
        if existing_ttl > (self.CODE_TTL_SECONDS - self.COOLDOWN_SECONDS):
            retry_after = int(existing_ttl - (self.CODE_TTL_SECONDS - self.COOLDOWN_SECONDS))
            return {"status": "cooldown", "retry_after": retry_after}

        code = self._generate_code()
        data = {
            "code": code,
            "attempts": 0,
            "verified": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.redis.setex(key, self.CODE_TTL_SECONDS, str(data))

        send_result = self._deliver_code(phone, code, send_via)
        if send_result.get("ok") or send_result.get("status") == "sent":
            logger.info("Verification code sent to %s via %s", phone, send_via)
            return {
                "status": "sent",
                "phone": phone,
                "expires_in": self.CODE_TTL_SECONDS,
                "attempts_left": self.MAX_ATTEMPTS,
                "channel": send_via,
            }

        self.redis.delete(key)
        return {"status": "error", "detail": f"Failed to send via {send_via}"}

    def verify_code(self, phone_number: str, code: str) -> dict[str, Any]:
        """Verify code entered by user."""
        phone = self._normalize_phone(phone_number)
        key = self._key(phone)

        raw = self.redis.get(key)
        if not raw:
            return {"status": "expired"}

        try:
            data = ast.literal_eval(raw.decode())
        except (ValueError, SyntaxError):
            self.redis.delete(key)
            return {"status": "expired"}

        if data.get("verified"):
            return {"status": "already_verified", "phone": phone}

        attempts = data.get("attempts", 0)
        if attempts >= self.MAX_ATTEMPTS:
            self.redis.delete(key)
            return {"status": "max_attempts_exceeded"}

        if data["code"] == code.strip():
            data["verified"] = True
            data["verified_at"] = datetime.now(timezone.utc).isoformat()
            self.redis.setex(key, 3600, str(data))
            logger.info("Phone %s verified successfully", phone)
            return {"status": "verified", "phone": phone}

        data["attempts"] = attempts + 1
        remaining = self.MAX_ATTEMPTS - data["attempts"]
        current_ttl = self.redis.ttl(key)
        self.redis.setex(key, max(current_ttl, 1), str(data))

        if remaining <= 0:
            self.redis.delete(key)
            return {"status": "max_attempts_exceeded"}

        return {"status": "invalid", "attempts_left": remaining}

    def get_status(self, phone_number: str) -> dict[str, Any]:
        """Get verification status."""
        phone = self._normalize_phone(phone_number)
        key = self._key(phone)
        raw = self.redis.get(key)
        if not raw:
            return {"status": "not_found"}
        try:
            data = ast.literal_eval(raw.decode())
        except (ValueError, SyntaxError):
            return {"status": "not_found"}
        return {
            "status": "verified" if data.get("verified") else "pending",
            "phone": phone,
            "ttl_seconds": self.redis.ttl(key),
            "attempts_used": data.get("attempts", 0),
            "attempts_left": self.MAX_ATTEMPTS - data.get("attempts", 0),
        }

    def revoke(self, phone_number: str) -> bool:
        phone = self._normalize_phone(phone_number)
        return bool(self.redis.delete(self._key(phone)))

    def _deliver_code(self, phone: str, code: str, channel: str) -> dict[str, Any]:
        if channel == "max":
            return self._send_via_max(phone, code)
        elif channel == "sms":
            return self._send_via_sms(phone, code)
        return {"ok": False, "error": f"Unknown channel: {channel}"}

    def _send_via_max(self, phone: str, code: str) -> dict[str, Any]:
        from app.integrations.max.service import MAXService
        svc = MAXService()
        text = (
            f"<b>🔐 Код подтверждения</b>\n\n"
            f"Ваш код для регистрации:\n"
            f"<code>{code}</code>\n\n"
            f"Никому не сообщайте. Действителен 10 минут."
        )
        return svc.send_message(phone_number=phone, text=text)

    def _send_via_sms(self, phone: str, code: str) -> dict[str, Any]:
        from app.integrations.sms.service import SMSService
        svc = SMSService()
        message = f"Код подтверждения: {code}. Не сообщайте никому. FitIntel Pro"
        return svc.send(phone=phone, message=message)

    def send_code_with_fallback(self, phone_number: str, channels: list[str] | None = None) -> dict[str, Any]:
        channels = channels or ["max", "sms"]
        for channel in channels:
            result = self.send_code(phone_number, send_via=channel)
            if result["status"] == "sent":
                result["channel_used"] = channel
                return result
            if result["status"] == "cooldown":
                return result
        return {"status": "error", "detail": "All channels failed"}


_verification_service: PhoneVerificationService | None = None


def get_phone_verification_service() -> PhoneVerificationService:
    global _verification_service
    if _verification_service is None:
        _verification_service = PhoneVerificationService()
    return _verification_service
