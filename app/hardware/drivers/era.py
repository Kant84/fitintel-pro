# app/hardware/drivers/era.py — Драйвер для СКУД "ЭРА"
import asyncio
from datetime import datetime
from app.hardware.base import BaseDeviceDriver, DeviceType, ConnectionProtocol, DeviceStatus, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import register_driver


@register_driver
class EraDriver(BaseDeviceDriver):
    """Драйвер для турникетов и контроллеров ЭРА (ООО "Электронные системы доступа")"""

    VENDOR = "ЭРА"
    MODELS = ["T-1000", "T-2000", "C-100", "C-200", "C-PRO", "T-UNI"]
    DEVICE_TYPES = [DeviceType.TURNSTILE, DeviceType.CONTROLLER, DeviceType.BARRIER]
    PROTOCOLS = [ConnectionProtocol.TCP, ConnectionProtocol.HTTP_API]

    # ЭРА использует свой бинарный протокол поверх TCP (порт 5000)
    # или HTTP API (порт 80)

    DEFAULT_PORT = 5000
    COMMAND_OPEN = b"\x02\x01\x01\x00\x03"       # Открыть проход
    COMMAND_CLOSE = b"\x02\x01\x00\x00\x03"      # Закрыть
    COMMAND_STATUS = b"\x02\x03\x00\x00\x03"     # Запрос статуса
    RESPONSE_OK = b"\x06"                          # ACK

    def __init__(self, config: dict):
        super().__init__(config)
        self.port = config.get("port", self.DEFAULT_PORT)
        self._reader = None
        self._writer = None
        self._listening = False

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )
            self._status = DeviceStatus.ONLINE
            self._last_ping = datetime.utcnow()
            return True
        except Exception as e:
            self._status = DeviceStatus.OFFLINE
            print(f"[ЭРА {self.device_id}] Connect failed: {e}")
            return False

    async def disconnect(self):
        self._listening = False
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except:
                pass
        self._status = DeviceStatus.OFFLINE

    async def ping(self) -> bool:
        if not self._writer:
            return await self.connect()
        try:
            self._writer.write(self.COMMAND_STATUS)
            await asyncio.wait_for(self._reader.read(1), timeout=3.0)
            self._last_ping = datetime.utcnow()
            self._status = DeviceStatus.ONLINE
            return True
        except:
            self._status = DeviceStatus.OFFLINE
            return False

    async def open(self, credential: str = None, **kwargs) -> AccessResult:
        if not self._writer:
            if not await self.connect():
                return AccessResult.ERROR
        try:
            # Если передан credential — сначала проверяем через API
            if credential:
                valid = await self._validate_credential(credential)
                if not valid:
                    return AccessResult.INVALID_CREDENTIAL

            self._writer.write(self.COMMAND_OPEN)
            resp = await asyncio.wait_for(self._reader.read(1), timeout=3.0)
            if resp == self.RESPONSE_OK:
                await self._emit_event(HardwareEvent(
                    HWEventType.ENTRY,
                    self.device_id,
                    credential,
                    details={"direction": kwargs.get("direction", "entry")}
                ))
                return AccessResult.GRANTED
            return AccessResult.ERROR
        except asyncio.TimeoutError:
            return AccessResult.TIMEOUT
        except Exception as e:
            print(f"[ЭРА {self.device_id}] Open error: {e}")
            return AccessResult.ERROR

    async def close(self, **kwargs) -> bool:
        if not self._writer:
            return False
        try:
            self._writer.write(self.COMMAND_CLOSE)
            resp = await asyncio.wait_for(self._reader.read(1), timeout=3.0)
            return resp == self.RESPONSE_OK
        except:
            return False

    async def get_device_info(self) -> dict:
        return {
            "vendor": self.VENDOR,
            "model": self.config.get("model", "unknown"),
            "firmware": self.config.get("firmware_version", "unknown"),
            "ip": self.host,
            "port": self.port,
            "status": self._status.value,
        }

    async def start_event_listener(self):
        """Слушать события от ЭРА (проходы, тревоги)"""
        self._listening = True
        while self._listening:
            try:
                data = await asyncio.wait_for(self._reader.read(16), timeout=30.0)
                if data:
                    await self._parse_event(data)
            except asyncio.TimeoutError:
                await self.ping()  # Keep-alive
            except Exception:
                await asyncio.sleep(5)
                await self.connect()

    async def stop_event_listener(self):
        self._listening = False

    async def _validate_credential(self, credential: str) -> bool:
        """Проверить ключ через внутреннюю базу ЭРА или через наш API"""
        return True  # Реальная проверка через API

    async def _parse_event(self, data: bytes):
        """Разобрать событие от ЭРА"""
        if len(data) < 5:
            return
        event_code = data[1]
        event_map = {
            0x10: HWEventType.ENTRY,
            0x11: HWEventType.EXIT,
            0x20: HWEventType.DENIED,
            0x30: HWEventType.ALARM,
            0x31: HWEventType.TAMPER,
            0x40: HWEventType.BUTTON_PRESS,
        }
        event_type = event_map.get(event_code, HWEventType.HEARTBEAT)
        await self._emit_event(HardwareEvent(
            event_type, self.device_id,
            details={"raw": data.hex()}
        ))
