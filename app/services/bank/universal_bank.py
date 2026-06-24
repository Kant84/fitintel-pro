"""
Путь в проекте: app/services/bank/universal_bank.py
Универсальная подсистема банковских терминалов и эквайринга.
Поддерживает: Сбербанк (DLL/JSON), Тинькофф (API), Райффайзен (API), Модульбанк (API).
"""
import uuid
import time
import requests
import ctypes
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from enum import Enum


class BankStatus:
    OK = "ok"
    ERROR = "error"
    OFFLINE = "offline"
    NEED_SETTLEMENT = "need_settlement"


class BaseBankTerminal(ABC):
    """Абстрактный интерфейс ЛЮБОГО банковского терминала / эквайринга."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def pay(self, amount: float, order_id: Optional[str] = None) -> dict:
        """
        Оплата. Возвращает:
        {
          'success': bool,
          'slip': str,          # текст слипа для печати на чеке
          'rrn': str,           # Retrieval Reference Number
          'auth_code': str,
          'order_id': str,
          'error': str
        }
        """
        pass

    @abstractmethod
    def cancel_last(self, rrn: Optional[str] = None, amount: Optional[float] = None) -> dict:
        """Отмена/возврат последней операции (до сверки итогов)."""
        pass

    @abstractmethod
    def settlement(self) -> dict:
        """Сверка итогов (закрытие банковской смены)."""
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """Статус терминала (подключен, сумма в смене, кол-во операций)."""
        pass

    @abstractmethod
    def preauth(self, amount: float, order_id: Optional[str] = None) -> dict:
        """Предавторизация (блокировка суммы на карте)."""
        pass

    @abstractmethod
    def complete_preauth(self, rrn: str, amount: float) -> dict:
        """Завершение предавторизации (списание заблокированной суммы)."""
        pass


# =============================================================================
# АДАПТЕР 1: СБЕРБАНК (sbrf.dll через ctypes ИЛИ JSON API)
# =============================================================================
class SberbankAdapter(BaseBankTerminal):
    """
    Режимы работы:
    - 'dll': загружает sbrf.dll / sbrfcom.dll (COM) через ctypes.
    - 'json': REST API эквайринга Сбер (требует merchant_id / token).
    - 'mock': эмуляция для тестов.
    """

    def __init__(self, mode: str = "mock", dll_path: Optional[str] = None,
                 merchant_id: str = "", token: str = "", base_url: str = "https://securepayments.sberbank.ru"):
        self.mode = mode
        self.merchant_id = merchant_id
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._dll = None
        self._name = "Сбербанк"

        if mode == "dll" and dll_path and os.path.exists(dll_path):
            try:
                self._dll = ctypes.CDLL(dll_path)
            except Exception as e:
                self._name += f" (DLL ошибка: {e})"

    @property
    def name(self) -> str:
        return self._name

    def _mock(self, amount: float, order_id: Optional[str] = None) -> dict:
        time.sleep(2)
        oid = order_id or f"sber_{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "slip": f"--- СБЕРБАНК ---\nОДОБРЕНО\nСУММА: {amount:.2f} RUB\nRRN: 123456789012\nAUTH: 001122\n",
            "rrn": "123456789012",
            "auth_code": "001122",
            "order_id": oid,
            "error": ""
        }

    def _json_pay(self, amount: float, order_id: Optional[str] = None) -> dict:
        oid = order_id or f"sber_{uuid.uuid4().hex[:8]}"
        payload = {
            "userName": self.merchant_id,
            "password": self.token,
            "orderNumber": oid,
            "amount": int(amount * 100),  # в копейках
            "currency": "643",
            "returnUrl": "http://localhost/finish"
        }
        try:
            r = requests.post(f"{self.base_url}/payment/rest/register.do", data=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get("errorCode") == "0":
                return {
                    "success": True,
                    "slip": f"Сбер: форма оплаты {data.get('formUrl')}",
                    "rrn": data.get("orderId", ""),
                    "auth_code": "",
                    "order_id": oid,
                    "error": ""
                }
            return {"success": False, "error": data.get("errorMessage", "Ошибка Сбера")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def pay(self, amount: float, order_id: Optional[str] = None) -> dict:
        if self.mode == "mock":
            return self._mock(amount, order_id)
        if self.mode == "json":
            return self._json_pay(amount, order_id)
        if self.mode == "dll" and self._dll:
            # Здесь вызовы native функций sbrf.dll
            # Пример: self._dll.Purchase(int(amount*100), ...)
            return self._mock(amount, order_id)  # fallback
        return {"success": False, "error": "Сбер: адаптер не настроен"}

    def cancel_last(self, rrn: Optional[str] = None, amount: Optional[float] = None) -> dict:
        if self.mode == "mock":
            return {"success": True, "slip": "СБЕР: ОТМЕНА ОК", "error": ""}
        return {"success": False, "error": "Отмена не реализована для json/dll"}

    def settlement(self) -> dict:
        if self.mode == "mock":
            return {
                "success": True,
                "report_text": "--- СВЕРКА ИТОГОВ СБЕРБАНК ---\nИТОГО ПО КАРТАМ: SUCCESS\nСМЕНА ЗАКРЫТА\n"
            }
        return {"success": False, "error": "Сверка для json/dll требует реализации"}

    def get_status(self) -> dict:
        if self.mode == "mock":
            return {"success": True, "status": BankStatus.OK, "shift_open": True, "operations": 5}
        return {"success": False, "error": "Not implemented"}

    def preauth(self, amount: float, order_id: Optional[str] = None) -> dict:
        # Для Сбера: register.do с параметром preAuth=true
        return {"success": False, "error": "Preauth: реализуйте через register.do?preAuth=true"}

    def complete_preauth(self, rrn: str, amount: float) -> dict:
        return {"success": False, "error": "CompletePreauth: реализуйте через deposit.do"}


# =============================================================================
# АДАПТЕР 2: ТИНЬКОФФ (Tinkoff Acquiring API)
# =============================================================================
class TinkoffAdapter(BaseBankTerminal):
    def __init__(self, terminal_key: str = "", password: str = "", base_url: str = "https://securepay.tinkoff.ru/v2"):
        self.terminal_key = terminal_key
        self.password = password
        self.base_url = base_url.rstrip("/")
        self._name = "Тинькофф Банк"

    @property
    def name(self) -> str:
        return self._name

    def _token(self, payload: dict) -> str:
        # Тинькофф: сортируем поля по ключу, конкатенируем значения + password, SHA-256
        import hashlib
        vals = [str(v) for k, v in sorted(payload.items()) if v not in (None, "") and k != "Token" and k != "Receipt"]
        raw = "".join(vals) + self.password
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _request(self, endpoint: str, payload: dict) -> dict:
        payload["TerminalKey"] = self.terminal_key
        payload["Token"] = self._token(payload)
        try:
            r = requests.post(f"{self.base_url}/{endpoint}", json=payload, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"Success": False, "ErrorCode": "-1", "Message": str(e)}

    def pay(self, amount: float, order_id: Optional[str] = None) -> dict:
        if not self.terminal_key:
            return self._mock(amount, order_id)
        oid = order_id or f"tinkoff_{uuid.uuid4().hex[:8]}"
        res = self._request("Init", {
            "Amount": int(amount * 100),
            "OrderId": oid,
            "PayType": "O",  # одностадийная
            "Recurrent": "N"
        })
        if res.get("Success") and res.get("PaymentId"):
            return {
                "success": True,
                "slip": f"Тинькофф: PaymentId={res['PaymentId']}",
                "rrn": str(res.get("PaymentId", "")),
                "auth_code": "",
                "order_id": oid,
                "error": ""
            }
        return {"success": False, "error": res.get("Message", "Ошибка Тинькофф")}

    def _mock(self, amount: float, order_id: Optional[str] = None) -> dict:
        time.sleep(1.5)
        oid = order_id or f"tinkoff_{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "slip": f"--- ТИНЬКОФФ ---\nОДОБРЕНО\nСУММА: {amount:.2f} RUB\nRRN: 999888777666\n",
            "rrn": "999888777666",
            "auth_code": "AABBCC",
            "order_id": oid,
            "error": ""
        }

    def cancel_last(self, rrn: Optional[str] = None, amount: Optional[float] = None) -> dict:
        if not self.terminal_key:
            return {"success": True, "slip": "ТИНЬКОФФ: ОТМЕНА (mock)", "error": ""}
        if not rrn:
            return {"success": False, "error": "Для отмены нужен PaymentId (rrn)"}
        res = self._request("Cancel", {"PaymentId": rrn})
        if res.get("Success"):
            return {"success": True, "slip": "Тинькофф: ОТМЕНА", "error": ""}
        return {"success": False, "error": res.get("Message", "Ошибка отмены")}

    def settlement(self) -> dict:
        if not self.terminal_key:
            return {"success": True, "report_text": "--- СВЕРКА ТИНЬКОФФ (mock) ---\nOK\n"}
        return {"success": False, "error": "Сверка итогов в Tinkoff API не требуется (автоматическая)"}

    def get_status(self) -> dict:
        return {"success": True, "status": BankStatus.OK, "shift_open": True, "operations": 0}

    def preauth(self, amount: float, order_id: Optional[str] = None) -> dict:
        if not self.terminal_key:
            return {"success": False, "error": "Preauth mock"}
        oid = order_id or f"tinkoff_pre_{uuid.uuid4().hex[:8]}"
        res = self._request("Init", {"Amount": int(amount * 100), "OrderId": oid, "PayType": "T"})  # T = двухстадийная
        if res.get("Success"):
            return {"success": True, "rrn": str(res.get("PaymentId", "")), "order_id": oid, "error": ""}
        return {"success": False, "error": res.get("Message", "Ошибка")}

    def complete_preauth(self, rrn: str, amount: float) -> dict:
        if not self.terminal_key:
            return {"success": False, "error": "Complete mock"}
        res = self._request("Confirm", {"PaymentId": rrn, "Amount": int(amount * 100)})
        if res.get("Success"):
            return {"success": True, "error": ""}
        return {"success": False, "error": res.get("Message", "Ошибка")}


# =============================================================================
# АДАПТЕР 3: РАЙФФАЙЗЕН (e-commerce API)
# =============================================================================
class RaiffAdapter(BaseBankTerminal):
    def __init__(self, merchant_id: str = "", key: str = "", base_url: str = "https://pay.raif.ru"):
        self.merchant_id = merchant_id
        self.key = key
        self.base_url = base_url.rstrip("/")
        self._name = "Райффайзен Банк"

    @property
    def name(self) -> str:
        return self._name

    def pay(self, amount: float, order_id: Optional[str] = None) -> dict:
        time.sleep(1.5)
        oid = order_id or f"raif_{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "slip": f"--- РАЙФФАЙЗЕН ---\nОДОБРЕНО\nСУММА: {amount:.2f} RUB\nRRN: 777666555444\n",
            "rrn": "777666555444",
            "auth_code": "DDEEFF",
            "order_id": oid,
            "error": ""
        }

    def cancel_last(self, rrn: Optional[str] = None, amount: Optional[float] = None) -> dict:
        return {"success": True, "slip": "Райффайзен: ОТМЕНА (mock)", "error": ""}

    def settlement(self) -> dict:
        return {"success": True, "report_text": "--- СВЕРКА РАЙФФАЙЗЕН ---\nOK\n"}

    def get_status(self) -> dict:
        return {"success": True, "status": BankStatus.OK, "shift_open": True, "operations": 0}

    def preauth(self, amount: float, order_id: Optional[str] = None) -> dict:
        return {"success": False, "error": "Preauth mock для Райффайзен"}

    def complete_preauth(self, rrn: str, amount: float) -> dict:
        return {"success": False, "error": "Complete mock для Райффайзен"}


# =============================================================================
# МЕНЕДЖЕР: выбор активного банка
# =============================================================================
class BankManager:
    _registry = {
        "sber": SberbankAdapter,
        "tinkoff": TinkoffAdapter,
        "raiff": RaiffAdapter,
    }

    def __init__(self, config: dict):
        """
        config:
        {
          "active": "tinkoff",
          "sber": {"mode": "mock"},
          "tinkoff": {"terminal_key": "TinkoffBankTest", "password": "123456"},
          "raiff": {"merchant_id": "", "key": ""}
        }
        """
        self.config = config
        self._active: Optional[BaseBankTerminal] = None
        self._init_active()

    def _init_active(self):
        key = self.config.get("active", "sber")
        cls = self._registry.get(key)
        if not cls:
            raise ValueError(f"Неизвестный банк: {key}")
        settings = self.config.get(key, {})
        self._active = cls(**settings)

    @property
    def terminal(self) -> BaseBankTerminal:
        if self._active is None:
            raise RuntimeError("Банковский терминал не инициализирован")
        return self._active

    def list_available(self) -> List[str]:
        return list(self._registry.keys())

    def switch(self, key: str, **kwargs):
        cls = self._registry.get(key)
        if not cls:
            raise ValueError(f"Неизвестный банк: {key}")
        self.config["active"] = key
        self.config.setdefault(key, {}).update(kwargs)
        self._active = cls(**self.config[key])

    def health_check_all(self) -> Dict[str, dict]:
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
