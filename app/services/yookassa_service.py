# app/services/yookassa_service.py
"""
YooKassa (ЮKassa) — онлайн-платежи.
Создание платежей, проверка статуса, возвраты.
"""

import os
import base64
import json
import urllib.request
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.orm import Session


YOOKASSA_API = "https://api.yookassa.ru/v3"


class YooKassaService:
    """Интеграция с YooKassa для онлайн-оплаты"""

    def __init__(self, db: Session):
        self.db = db
        self.shop_id = os.getenv("YOOKASSA_SHOP_ID", "")
        self.secret_key = os.getenv("YOOKASSA_SECRET_KEY", "")
        self.enabled = bool(self.shop_id and self.secret_key)

    def _auth_header(self) -> str:
        """Basic Auth заголовок"""
        credentials = base64.b64encode(f"{self.shop_id}:{self.secret_key}".encode()).decode()
        return f"Basic {credentials}"

    def _api(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Вызов YooKassa API"""
        if not self.enabled:
            return {"error": "YooKassa not configured", "mock": True}

        url = f"{YOOKASSA_API}{endpoint}"
        headers = {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
            "Idempotence-Key": str(uuid4()),
        }

        try:
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "body": e.read().decode()}
        except Exception as e:
            return {"error": str(e)}

    def create_payment(self, amount: float, description: str, return_url: str,
                       client_email: str = "", metadata: dict = None) -> dict:
        """
        Создать платёж.

        amount — сумма в рублях
        description — описание
        return_url — куда редиректнуть после оплаты
        """
        if not self.enabled:
            return self._mock_payment(amount, description)

        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": description[:128],
            "metadata": metadata or {},
        }

        if client_email:
            payload["receipt"] = {
                "customer": {"email": client_email},
                "items": [{
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                    "vat_code": 1,
                }],
            }

        return self._api("POST", "/payments", payload)

    def get_payment(self, payment_id: str) -> dict:
        """Получить статус платежа"""
        return self._api("GET", f"/payments/{payment_id}")

    def cancel_payment(self, payment_id: str) -> dict:
        """Отменить платёж"""
        return self._api("POST", f"/payments/{payment_id}/cancel")

    def create_refund(self, payment_id: str, amount: float) -> dict:
        """Создать возврат"""
        payload = {
            "payment_id": payment_id,
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB",
            },
        }
        return self._api("POST", "/refunds", payload)

    def handle_webhook(self, payload: dict) -> dict:
        """Обработка webhook от YooKassa"""
        event = payload.get("event", "")
        payment_obj = payload.get("object", {})

        if event == "payment.succeeded":
            return {
                "status": "success",
                "payment_id": payment_obj.get("id"),
                "amount": payment_obj.get("amount", {}).get("value"),
                "metadata": payment_obj.get("metadata", {}),
            }
        elif event == "payment.canceled":
            return {
                "status": "canceled",
                "payment_id": payment_obj.get("id"),
            }
        elif event == "refund.succeeded":
            return {
                "status": "refunded",
                "refund_id": payment_obj.get("id"),
                "payment_id": payment_obj.get("payment_id"),
            }

        return {"status": "unknown_event", "event": event}

    def _mock_payment(self, amount: float, description: str) -> dict:
        """Мок-платёж для тестирования без реальных ключей"""
        payment_id = f"mock-{uuid4().hex[:12]}"
        return {
            "id": payment_id,
            "status": "pending",
            "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
            "description": description,
            "confirmation": {
                "type": "redirect",
                "confirmation_url": f"https://yookassa.ru/payments/{payment_id}?mock=true",
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mock": True,
        }
