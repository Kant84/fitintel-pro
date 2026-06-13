# app/services/fiscal_service.py
"""
54-ФЗ Фискализация чеков.
Поддержка Атол, Эвотор, и универсальный ОФД-шлюз.
"""

import os
import urllib.request
import urllib.parse
import json
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import Session


class TaxSystem(str, Enum):
    OSN = "osn"           # Общая
    USN_INCOME = "usn_income"  # УСН доход
    USN_INCOME_EXPENSE = "usn_income_expense"
    ENVD = "envd"
    ESHN = "eshn"
    PATENT = "patent"


class PaymentType(str, Enum):
    CASH = "cash"         # Наличные
    ELECTRONIC = "electronic"  # Безнал
    PREPAID = "prepaid"   # Предоплата
    CREDIT = "credit"     # Постоплата
    OTHER = "other"       # Иное


class FiscalService:
    """Фискализация чеков по 54-ФЗ"""

    # ===== АТОЛ ОНЛАЙН =====
    ATOL_API = "https://online.atol.ru/possystem/v5"

    # ===== ЭВАТОР =====
    EVOTOR_API = "https://api.evotor.ru/api/v1/inventories"

    # ===== МОК-РЕЖИМ =====
    MOCK_MODE = os.getenv("FISCAL_MOCK", "true").lower() == "true"

    def __init__(self, db: Session):
        self.db = db
        self.provider = os.getenv("FISCAL_PROVIDER", "atol")  # atol | evotor | mock
        self.atol_login = os.getenv("ATOL_LOGIN", "")
        self.atol_pass = os.getenv("ATOL_PASSWORD", "")
        self.group_code = os.getenv("ATOL_GROUP_CODE", "")
        self.inn = os.getenv("FISCAL_INN", "")

    def _atol_auth(self) -> str:
        """Получить токен Атол"""
        if self.MOCK_MODE:
            return "mock_token"
        url = f"{self.ATOL_API}/getToken"
        data = json.dumps({"login": self.atol_login, "pass": self.atol_pass}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("token", "")
        except Exception:
            return ""

    def create_receipt(
        self,
        receipt_type: str,  # "sell" | "sell_refund"
        items: list[dict],
        total: float,
        payment_type: PaymentType = PaymentType.ELECTRONIC,
        client_email: str = "",
        client_phone: str = "",
        external_id: str = "",
    ) -> dict:
        """
        Создать фискальный чек.
        
        items: [{"name": str, "price": float, "quantity": float, "sum": float}]
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if self.MOCK_MODE:
            return self._mock_receipt(receipt_type, items, total, external_id)

        token = self._atol_auth()
        if not token:
            return {"error": "Failed to authenticate with fiscal provider"}

        receipt_data = {
            "timestamp": timestamp,
            "external_id": external_id or f"fitintel-{datetime.now().timestamp()}",
            "receipt": {
                "client": {},
                "company": {
                    "email": os.getenv("COMPANY_EMAIL", ""),
                    "sno": self._map_tax_system(),
                    "inn": self.inn,
                    "payment_address": os.getenv("COMPANY_URL", ""),
                },
                "items": [
                    {
                        "name": item["name"][:128],
                        "price": int(item["price"] * 100),
                        "quantity": item["quantity"],
                        "sum": int(item["sum"] * 100),
                        "payment_method": "full_payment",
                        "payment_object": "service",
                        "vat": {"type": "vat20"},
                    }
                    for item in items
                ],
                "payments": [
                    {
                        "type": payment_type.value,
                        "sum": int(total * 100),
                    }
                ],
                "total": int(total * 100),
            }
        }

        if client_email:
            receipt_data["receipt"]["client"]["email"] = client_email
        if client_phone:
            receipt_data["receipt"]["client"]["phone"] = client_phone

        url = f"{self.ATOL_API}/{self.group_code}/{receipt_type}"
        data = json.dumps(receipt_data).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json", "Token": token}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}", "body": e.read().decode()}
        except Exception as e:
            return {"error": str(e)}

    def check_status(self, receipt_uuid: str) -> dict:
        """Проверить статус чека"""
        if self.MOCK_MODE:
            return {"status": "done", "uuid": receipt_uuid, "payload": {"fn_number": "mock_fn", "fiscal_document_number": 1}}

        token = self._atol_auth()
        url = f"{self.ATOL_API}/{self.group_code}/report/{receipt_uuid}"
        req = urllib.request.Request(url, headers={"Token": token})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def get_receipt_url(self, receipt_uuid: str) -> str:
        """Получить URL чека для клиента"""
        if self.MOCK_MODE:
            return f"https://checko.com/check/{receipt_uuid}"
        return f"https://check.atol.ru/{receipt_uuid}"

    def _mock_receipt(self, receipt_type: str, items: list, total: float, external_id: str) -> dict:
        """Мок-фискализация для тестирования"""
        return {
            "uuid": f"mock-{datetime.now().timestamp()}",
            "status": "wait",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mock": True,
            "receipt_type": receipt_type,
            "total": total,
            "items_count": len(items),
            "external_id": external_id,
            "ofd_receipt_url": f"https://checko.com/check/mock-{datetime.now().timestamp()}",
        }

    def _map_tax_system(self) -> str:
        """Код налоговой системы для Атол"""
        mapping = {
            "osn": "osn",
            "usn_income": "usn_income",
            "usn_income_expense": "usn_income_outcome",
            "envd": "envd",
            "eshn": "eshn",
            "patent": "patent",
        }
        return mapping.get(os.getenv("TAX_SYSTEM", "usn_income"), "usn_income")

    # ===== ОФД ПРЯМОЙ =====

    def send_to_ofd(self, receipt_data: dict) -> dict:
        """Отправить чек напрямую в ОФД"""
        ofd_url = os.getenv("OFD_API_URL", "")
        if not ofd_url:
            return {"error": "OFD URL not configured"}

        try:
            data = json.dumps(receipt_data).encode()
            req = urllib.request.Request(
                ofd_url, data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {"status": "sent", "ofd_response": json.loads(resp.read().decode())}
        except Exception as e:
            return {"error": str(e)}
