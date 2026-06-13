# app/hardware/base.py — Абстрактный интерфейс для всех СКУД-устройств
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
from datetime import datetime
import asyncio


class DeviceType(str, Enum):
    TURNSTILE = "turnstile"           # Турникет
    LOCKER = "locker"                 # Шкафчик
    ELECTRIC_LOCK = "electric_lock"   # Электрозамок
    CONTROLLER = "controller"         # Контроллер доступа
    READER = "reader"                 # Считыватель (QR/RFID/NFC/Face)
    POS_TERMINAL = "pos_terminal"     # Кассовый терминал
    INTERCOM = "intercom"             # Домофон
    BARRIER = "barrier"               # Шлагбаум
    GATE = "gate"                     # Распашные ворота
    FINGERPRINT = "fingerprint"       # Отпечаток пальца
    FACEID = "faceid"                 # Распознавание лиц


class ConnectionProtocol(str, Enum):
    TCP = "tcp"                       # Прямое TCP-соединение
    HTTP_API = "http_api"             # REST API устройства
    WEBSOCKET = "websocket"           # WebSocket
    MQTT = "mqtt"                     # MQTT брокер
    RS485 = "rs485"                   # RS-485 через serial/tcp-шлюз
    MODBUS_TCP = "modbus_tcp"         # Modbus TCP
    MODBUS_RTU = "modbus_rtu"         # Modbus RTU
    SOAP = "soap"                     # SOAP (для старых СКУД)
    SDK = "sdk"                       # Нативный SDK производителя
    SERIAL = "serial"                 # Прямое COM-подключение
    UDP = "udp"                       # UDP-пакеты


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    BUSY = "busy"
    UNKNOWN = "unknown"


class AccessResult(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    TIMEOUT = "timeout"
    ERROR = "error"
    INVALID_CREDENTIAL = "invalid_credential"
    EXPIRED_SUBSCRIPTION = "expired_subscription"
    NO_ACTIVE_SUBSCRIPTION = "no_active_subscription"
    LOCKER_OCCUPIED = "locker_occupied"
    ANTIPASSBACK = "antipassback"
    BLACKLIST = "blacklist"


class HWEventType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    DENIED = "denied"
    ALARM = "alarm"
    TAMPER = "tamper"
    HEARTBEAT = "heartbeat"
    BUTTON_PRESS = "button_press"
    EMERGENCY = "emergency"
    POWER_LOSS = "power_loss"
    DOOR_FORCED = "door_forced"
    DOOR_LEFT_OPEN = "door_left_open"


class HardwareEvent:
    """Событие от устройства"""
    def __init__(
        self,
        event_type: HWEventType,
        device_id: str,
        credential: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        details: Optional[dict] = None
    ):
        self.event_type = event_type
        self.device_id = device_id
        self.credential = credential
        self.timestamp = timestamp or datetime.utcnow()
        self.details = details or {}


class BaseDeviceDriver(ABC):
    """Абстрактный базовый класс для всех драйверов СКУД"""

    # Переопределять в драйвере
    VENDOR: str = ""
    MODELS: list[str] = []           # Поддерживаемые модели
    DEVICE_TYPES: list[DeviceType] = []
    PROTOCOLS: list[ConnectionProtocol] = []

    def __init__(self, config: dict):
        self.config = config
        self.device_id = config.get("device_id", "")
        self.name = config.get("name", "")
        self.host = config.get("host", "")
        self.port = config.get("port", 0)
        self.protocol = config.get("protocol", "")
        self.auth = config.get("auth", {})      # login/password/api_key
        self.options = config.get("options", {})  # Доп. параметры
        self._status = DeviceStatus.UNKNOWN
        self._last_ping: Optional[datetime] = None
        self._event_handlers: list = []

    @property
    def status(self) -> DeviceStatus:
        return self._status

    @property
    def last_ping(self) -> Optional[datetime]:
        return self._last_ping

    # ========== ЖИЗНЕННЫЙ ЦИКЛ ==========

    @abstractmethod
    async def connect(self) -> bool:
        """Подключиться к устройству"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Отключиться"""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Проверка связи с устройством"""
        pass

    # ========== УПРАВЛЕНИЕ ДОСТУПОМ ==========

    @abstractmethod
    async def open(self, credential: Optional[str] = None, **kwargs) -> AccessResult:
        """Открыть проход (турникет/ворота/замок)"""
        pass

    @abstractmethod
    async def close(self, **kwargs) -> bool:
        """Закрыть/заблокировать"""
        pass

    async def grant_access(self, client_id: str, credential: str, **kwargs) -> AccessResult:
        """Разрешить доступ конкретному клиенту"""
        return await self.open(credential=credential, client_id=client_id, **kwargs)

    async def deny_access(self, reason: str = "", **kwargs) -> AccessResult:
        """Запретить доступ"""
        return AccessResult.DENIED

    # ========== ШКАФЧИКИ ==========

    async def release_locker(self, locker_id: str, **kwargs) -> bool:
        """Освободить шкафчик (только для locker-устройств)"""
        raise NotImplementedError("Это устройство не поддерживает шкафчики")

    async def get_locker_status(self, locker_id: str, **kwargs) -> dict:
        """Статус шкафчика"""
        raise NotImplementedError()

    # ========== КОНФИГУРАЦИЯ УСТРОЙСТВА ==========

    @abstractmethod
    async def get_device_info(self) -> dict:
        """Информация об устройстве"""
        pass

    async def sync_credentials(self, credentials: list[dict]) -> bool:
        """Синхронизировать список ключей на устройстве"""
        return True  # По умолчанию — управление через API

    async def add_credential(self, credential: str, credential_type: str = "qr", **kwargs) -> bool:
        """Добавить ключ на устройство"""
        return True

    async def remove_credential(self, credential: str) -> bool:
        """Удалить ключ с устройства"""
        return True

    # ========== СОБЫТИЯ ==========

    def on_event(self, handler):
        """Подписаться на события от устройства"""
        self._event_handlers.append(handler)

    async def _emit_event(self, event: HardwareEvent):
        """Отправить событие всем подписчикам"""
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")

    @abstractmethod
    async def start_event_listener(self):
        """Запустить прослушивание событий от устройства"""
        pass

    async def stop_event_listener(self):
        """Остановить прослушивание"""
        pass

    # ========== ВСПОМОГАТЕЛЬНОЕ ==========

    @classmethod
    def supports(cls, vendor: str, model: str) -> bool:
        """Проверить, поддерживает ли драйвер устройство"""
        return vendor.lower() == cls.VENDOR.lower() and model.upper() in [m.upper() for m in cls.MODELS]

    def to_dict(self) -> dict:
        return {
            "driver": self.__class__.__name__,
            "vendor": self.VENDOR,
            "device_id": self.device_id,
            "name": self.name,
            "status": self._status.value,
            "last_ping": self._last_ping.isoformat() if self._last_ping else None,
            "protocol": self.protocol,
        }
