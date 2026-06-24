"""
Путь в проекте: app/services/fiscal/universal_fiscal.py
Универсальная фискальная подсистема.
Поддерживает: АТОЛ, Штрих-М, Эвотор, Меркурий (и любую будущую кассу через BaseFiscalPrinter).
"""
import uuid
import time
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from enum import Enum


class PaymentTypeEnum(str, Enum):
    CASH = "cash"           # Наличные
    ELECTRONIC = "electronic" # Безнал
    PREPAID = "prepaid"       # Предоплата
    CREDIT = "credit"         # Кредит
    CONSIDERATION = "consideration"  # Встречное предоставление


class FiscalStatus:
    OK = "ok"
    ERROR = "error"
    OFFLINE = "offline"
    SHIFT_EXPIRED = "shift_expired"


class CheckItem:
    """Универсальная позиция чека."""
    def __init__(self, name: str, price: float, quantity: float = 1.0,
                 payment_method: str = "fullPrepayment",
                 payment_object: str = "service",
                 tax_type: str = "none",
                 department: int = 1):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.amount = round(price * quantity, 2)
        self.payment_method = payment_method  # fullPrepayment, fullPayment, advance, etc.
        self.payment_object = payment_object  # commodity, service, excise, etc.
        self.tax_type = tax_type            # none, vat0, vat10, vat20, etc.
        self.department = department

    def to_atol(self) -> dict:
        return {
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "amount": self.amount,
            "paymentMethod": self.payment_method,
            "paymentObject": self.payment_object,
            "tax": {"type": self.tax_type}
        }

    def to_shtrih(self) -> dict:
        # Штрих-М JSON API v2
        return {
            "type": "position",
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "amount": self.amount,
            "tax": {"type": self.tax_type},
            "paymentMethod": self.payment_method,
            "paymentObject": self.payment_object
        }

    def to_evotor(self) -> dict:
        return {
            "name": self.name,
            "type": "POSITION",
            "price": self.price,
            "quantity": self.quantity,
            "tax": self.tax_type.upper() if self.tax_type != "none" else "NO_VAT"
        }

    def to_mercury(self) -> dict:
        return {
            "productName": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "amount": self.amount,
            "taxType": self.tax_type,
            "paymentMethod": self.payment_method,
            "paymentObject": self.payment_object
        }


class BaseFiscalPrinter(ABC):
    """Абстрактный интерфейс ЛЮБОЙ онлайн-кассы."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def open_shift(self, operator_name: str = "Администратор") -> dict:
        """Открыть смену. Возвращает {'success': bool, 'error': str, 'data': ...}"""
        pass

    @abstractmethod
    def print_sale_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                         total: Optional[float] = None, slip: str = "") -> dict:
        """Пробить чек прихода."""
        pass

    @abstractmethod
    def print_return_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                           total: Optional[float] = None, slip: str = "") -> dict:
        """Пробить чек возврата."""
        pass

    @abstractmethod
    def close_shift(self, operator_name: str = "Администратор") -> dict:
        """Закрыть смену (Z-отчет)."""
        pass

    @abstractmethod
    def cancel_last_document(self) -> dict:
        """Аннулировать последний документ (до сверки)."""
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """Получить состояние кассы (дата, номер смены, непереданные документы)."""
        pass

    @abstractmethod
    def send_correction(self, items: List[CheckItem], reason: str) -> dict:
        """Чек коррекции (для 54-ФЗ)."""
        pass


# =============================================================================
# АДАПТЕР 1: АТОЛ (ДТО 10)
# =============================================================================
class AtolAdapter(BaseFiscalPrinter):
    def __init__(self, base_url: str = "http://127.0.0.1:16732", auth: Optional[tuple] = None):
        self.base_url = base_url.rstrip("/")
        self.requests_url = f"{self.base_url}/requests"
        self.auth = auth
        self._name = "АТОЛ ДТО 10"

    @property
    def name(self) -> str:
        return self._name

    def _send(self, command_type: str, payload_data: dict, operator: str = "Администратор") -> dict:
        task_uuid = str(uuid.uuid4())
        body = {
            "uuid": task_uuid,
            "request": {
                "type": command_type,
                "operator": {"name": operator},
                **payload_data
            }
        }
        try:
            r = requests.post(self.requests_url, json=body, auth=self.auth, timeout=10)
            r.raise_for_status()
        except requests.exceptions.ConnectionError:
            return {"success": False, "status": FiscalStatus.OFFLINE, "error": "АТОЛ не отвечает"}
        except requests.exceptions.Timeout:
            return {"success": False, "status": FiscalStatus.ERROR, "error": "Таймаут АТОЛ"}
        return self._poll(task_uuid)

    def _poll(self, task_uuid: str, attempts: int = 15, delay: float = 0.5) -> dict:
        for _ in range(attempts):
            time.sleep(delay)
            try:
                r = requests.get(f"{self.base_url}/results/{task_uuid}", auth=self.auth, timeout=5)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("status") == "ready":
                        return {"success": True, "status": FiscalStatus.OK, "data": d}
                    if d.get("status") == "error":
                        return {"success": False, "status": FiscalStatus.ERROR, "error": d.get("error", "Ошибка АТОЛ")}
            except Exception:
                continue
        return {"success": False, "status": FiscalStatus.ERROR, "error": "АТОЛ не ответил за время ожидания"}

    def open_shift(self, operator_name: str = "Администратор") -> dict:
        return self._send("openShift", {}, operator_name)

    def print_sale_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                         total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: 0, PaymentTypeEnum.ELECTRONIC: 1,
                  PaymentTypeEnum.PREPAID: 2, PaymentTypeEnum.CREDIT: 3, PaymentTypeEnum.CONSIDERATION: 4}
        payload = {
            "receipt": {
                "items": [i.to_atol() for i in items],
                "payments": [{"type": pt_map.get(payment_type, 1), "sum": total}],
                "additionalReceiptInfo": slip
            }
        }
        return self._send("sell", payload)

    def print_return_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                           total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: 0, PaymentTypeEnum.ELECTRONIC: 1,
                  PaymentTypeEnum.PREPAID: 2, PaymentTypeEnum.CREDIT: 3, PaymentTypeEnum.CONSIDERATION: 4}
        payload = {
            "receipt": {
                "items": [i.to_atol() for i in items],
                "payments": [{"type": pt_map.get(payment_type, 1), "sum": total}],
                "additionalReceiptInfo": slip
            }
        }
        return self._send("sellReturn", payload)

    def close_shift(self, operator_name: str = "Администратор") -> dict:
        return self._send("closeShift", {}, operator_name)

    def cancel_last_document(self) -> dict:
        return self._send("cancel", {})

    def get_status(self) -> dict:
        # ДТО 10 не имеет прямого /status, используем getDeviceInfo через requests
        return self._send("getDeviceInfo", {})

    def send_correction(self, items: List[CheckItem], reason: str) -> dict:
        total = sum(i.amount for i in items)
        payload = {
            "correction": {
                "type": "self",
                "reason": reason,
                "receipt": {
                    "items": [i.to_atol() for i in items],
                    "payments": [{"type": 1, "sum": total}]
                }
            }
        }
        return self._send("sellCorrection", payload)


# =============================================================================
# АДАПТЕР 2: ШТРИХ-М (JSON API v2 через Web Server)
# =============================================================================
class ShtrihAdapter(BaseFiscalPrinter):
    def __init__(self, base_url: str = "http://127.0.0.1:8080", password: str = "30"):
        self.base_url = base_url.rstrip("/")
        self.password = password
        self._name = "Штрих-М (Web Server)"

    @property
    def name(self) -> str:
        return self._name

    def _send(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        try:
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                return {"success": False, "error": data["error"], "data": data}
            return {"success": True, "data": data}
        except requests.exceptions.ConnectionError:
            return {"success": False, "status": FiscalStatus.OFFLINE, "error": "Штрих-М не отвечает"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_shift(self, operator_name: str = "Администратор") -> dict:
        return self._send("openShift", {"operator": operator_name})

    def print_sale_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                         total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: 0, PaymentTypeEnum.ELECTRONIC: 1, PaymentTypeEnum.PREPAID: 2}
        payload = {
            "type": "sell",
            "operator": operator_name,
            "items": [i.to_shtrih() for i in items],
            "payments": [{"type": pt_map.get(payment_type, 1), "sum": total}],
            "postItems": [{"type": "text", "text": slip}] if slip else []
        }
        return self._send("fiscal", payload)

    def print_return_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                           total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: 0, PaymentTypeEnum.ELECTRONIC: 1, PaymentTypeEnum.PREPAID: 2}
        payload = {
            "type": "sellReturn",
            "items": [i.to_shtrih() for i in items],
            "payments": [{"type": pt_map.get(payment_type, 1), "sum": total}]
        }
        return self._send("fiscal", payload)

    def close_shift(self, operator_name: str = "Администратор") -> dict:
        return self._send("closeShift", {"operator": operator_name})

    def cancel_last_document(self) -> dict:
        return self._send("cancelFiscal", {})

    def get_status(self) -> dict:
        return self._send("getStatus", {})

    def send_correction(self, items: List[CheckItem], reason: str) -> dict:
        total = sum(i.amount for i in items)
        payload = {
            "type": "sellCorrection",
            "correctionType": 0,  # самостоятельно
            "correctionReason": reason,
            "items": [i.to_shtrih() for i in items],
            "payments": [{"type": 1, "sum": total}]
        }
        return self._send("fiscal", payload)


# =============================================================================
# АДАПТЕР 3: ЭВОТОР (Cloud API)
# =============================================================================
class EvotorAdapter(BaseFiscalPrinter):
    def __init__(self, base_url: str = "https://api.evotor.ru", token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {"X-Authorization": token}
        self._name = "Эвотор Cloud"

    @property
    def name(self) -> str:
        return self._name

    def _send(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            if method == "GET":
                r = requests.get(url, headers=self.headers, timeout=10)
            else:
                r = requests.post(url, json=payload, headers=self.headers, timeout=10)
            r.raise_for_status()
            return {"success": True, "data": r.json()}
        except requests.exceptions.ConnectionError:
            return {"success": False, "status": FiscalStatus.OFFLINE, "error": "Эвотор не доступен"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_shift(self, operator_name: str = "Администратор") -> dict:
        # В Эвоторе смена открывается на устройстве автоматически при первом чеке
        return {"success": True, "message": "Смена откроется автоматически при печати чека"}

    def print_sale_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                         total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: "CASH", PaymentTypeEnum.ELECTRONIC: "CARD",
                  PaymentTypeEnum.PREPAID: "PREPAID", PaymentTypeEnum.CREDIT: "CREDIT"}
        payload = {
            "type": "SELL",
            "items": [i.to_evotor() for i in items],
            "payments": [{"type": pt_map.get(payment_type, "CARD"), "sum": total}],
            "deviceId": "auto"
        }
        return self._send("POST", "/api/v1/inventories/storefront/documents", payload)

    def print_return_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                           total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: "CASH", PaymentTypeEnum.ELECTRONIC: "CARD",
                  PaymentTypeEnum.PREPAID: "PREPAID", PaymentTypeEnum.CREDIT: "CREDIT"}
        payload = {
            "type": "PAYBACK",
            "items": [i.to_evotor() for i in items],
            "payments": [{"type": pt_map.get(payment_type, "CARD"), "sum": total}]
        }
        return self._send("POST", "/api/v1/inventories/storefront/documents", payload)

    def close_shift(self, operator_name: str = "Администратор") -> dict:
        # В Эвоторе Z-отчет формируется через документ
        payload = {"type": "CLOSE_SHIFT"}
        return self._send("POST", "/api/v1/inventories/storefront/documents", payload)

    def cancel_last_document(self) -> dict:
        return {"success": False, "error": "Эвотор: отмена через личный кабинет"}

    def get_status(self) -> dict:
        return self._send("GET", "/api/v1/inventories/stores")

    def send_correction(self, items: List[CheckItem], reason: str) -> dict:
        return {"success": False, "error": "Эвотор: коррекция через API v2 / личный кабинет"}


# =============================================================================
# АДАПТЕР 4: МЕРКУРИЙ (InfoSoft Web API)
# =============================================================================
class MercuryAdapter(BaseFiscalPrinter):
    def __init__(self, base_url: str = "http://127.0.0.1:5000", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._name = "Меркурий (InfoSoft)"

    @property
    def name(self) -> str:
        return self._name

    def _send(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        try:
            r = requests.post(url, json=payload, headers=self.headers, timeout=10)
            r.raise_for_status()
            return {"success": True, "data": r.json()}
        except requests.exceptions.ConnectionError:
            return {"success": False, "status": FiscalStatus.OFFLINE, "error": "Меркурий не отвечает"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_shift(self, operator_name: str = "Администратор") -> dict:
        return self._send("/api/openShift", {"operator": operator_name})

    def print_sale_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                         total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: "CASH", PaymentTypeEnum.ELECTRONIC: "ELECTRONICALLY",
                  PaymentTypeEnum.PREPAID: "PREPAID"}
        payload = {
            "type": "sell",
            "items": [i.to_mercury() for i in items],
            "payments": [{"type": pt_map.get(payment_type, "ELECTRONICALLY"), "sum": total}],
            "additionalInfo": slip
        }
        return self._send("/api/fiscal", payload)

    def print_return_check(self, items: List[CheckItem], payment_type: PaymentTypeEnum,
                           total: Optional[float] = None, slip: str = "") -> dict:
        if total is None:
            total = sum(i.amount for i in items)
        pt_map = {PaymentTypeEnum.CASH: "CASH", PaymentTypeEnum.ELECTRONIC: "ELECTRONICALLY",
                  PaymentTypeEnum.PREPAID: "PREPAID"}
        payload = {
            "type": "sellReturn",
            "items": [i.to_mercury() for i in items],
            "payments": [{"type": pt_map.get(payment_type, "ELECTRONICALLY"), "sum": total}]
        }
        return self._send("/api/fiscal", payload)

    def close_shift(self, operator_name: str = "Администратор") -> dict:
        return self._send("/api/closeShift", {"operator": operator_name})

    def cancel_last_document(self) -> dict:
        return self._send("/api/cancel", {})

    def get_status(self) -> dict:
        return self._send("/api/status", {})

    def send_correction(self, items: List[CheckItem], reason: str) -> dict:
        total = sum(i.amount for i in items)
        payload = {
            "type": "sellCorrection",
            "reason": reason,
            "items": [i.to_mercury() for i in items],
            "payments": [{"type": "ELECTRONICALLY", "sum": total}]
        }
        return self._send("/api/fiscal", payload)


# =============================================================================
# МЕНЕДЖЕР: выбор активной кассы из настроек
# =============================================================================
class FiscalManager:
    """Единая точка входа. В настройках клуба хранится 'active_fiscal': 'atol' | 'shtrih' | 'evotor' | 'mercury'."""

    _registry = {
        "atol": AtolAdapter,
        "shtrih": ShtrihAdapter,
        "evotor": EvotorAdapter,
        "mercury": MercuryAdapter,
    }

    def __init__(self, config: dict):
        """
        config пример:
        {
          "active": "atol",
          "atol": {"base_url": "http://127.0.0.1:16732"},
          "shtrih": {"base_url": "http://127.0.0.1:8080", "password": "30"},
          "evotor": {"token": "xxx"},
          "mercury": {"base_url": "http://127.0.0.1:5000", "api_key": "xxx"}
        }
        """
        self.config = config
        self._active: Optional[BaseFiscalPrinter] = None
        self._init_active()

    def _init_active(self):
        key = self.config.get("active", "atol")
        cls = self._registry.get(key)
        if not cls:
            raise ValueError(f"Неизвестная касса: {key}")
        settings = self.config.get(key, {})
        self._active = cls(**settings)

    @property
    def printer(self) -> BaseFiscalPrinter:
        if self._active is None:
            raise RuntimeError("Касса не инициализирована")
        return self._active

    def list_available(self) -> List[str]:
        return list(self._registry.keys())

    def switch(self, key: str, **kwargs):
        """Сменить активную кассу на лету."""
        cls = self._registry.get(key)
        if not cls:
            raise ValueError(f"Неизвестная касса: {key}")
        self.config["active"] = key
        self.config.setdefault(key, {}).update(kwargs)
        self._active = cls(**self.config[key])

    def health_check_all(self) -> Dict[str, dict]:
        """Проверить все настроенные кассы (для админ-панели)."""
        results = {}
        for key, cls in self._registry.items():
            settings = self.config.get(key, {})
            if not settings:
                results[key] = {"configured": False}
                continue
            try:
                inst = cls(**settings)
                st = inst.get_status()
                results[key] = {"configured": True, "status": st}
            except Exception as e:
                results[key] = {"configured": True, "error": str(e)}
        return results
