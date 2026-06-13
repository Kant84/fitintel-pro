# app/hardware/drivers/kerong.py — Драйвер для шкафчиков Kerong (RS-485 / TCP шлюз)
import asyncio
from datetime import datetime
from app.hardware.base import BaseDeviceDriver, DeviceType, ConnectionProtocol, DeviceStatus, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import register_driver


@register_driver
class KerongDriver(BaseDeviceDriver):
    """
    Драйвер для контроллеров шкафчиков Kerong.
    Работает через TCP-шлюз RS-485 (Modbus RTU поверх TCP).
    """

    VENDOR = "Kerong"
    MODELS = ["KR-S50", "KR-S100", "KR-S200", "KR-M16", "KR-M24", "KR-M40", "KR-PRO"]
    DEVICE_TYPES = [DeviceType.LOCKER]
    PROTOCOLS = [ConnectionProtocol.RS485, ConnectionProtocol.MODBUS_RTU, ConnectionProtocol.TCP]

    DEFAULT_PORT = 502           # TCP-шлюз (обычно преобразователь RS-485)
    MODBUS_SLAVE_ID = 1          # ID контроллера на шине

    # Modbus RTU функции
    FUNC_READ_HOLDING = 0x03
    FUNC_WRITE_SINGLE = 0x06
    FUNC_WRITE_MULTIPLE = 0x10

    # Адреса регистров (зависят от модели)
    REG_STATUS_BASE = 0x0000      # Базовый адрес статуса шкафчиков
    REG_OPEN_BASE = 0x1000       # Базовый адрес открытия
    REG_LED_BASE = 0x2000        # Управление LED

    def __init__(self, config: dict):
        super().__init__(config)
        self.port = config.get("port", self.DEFAULT_PORT)
        self.slave_id = config.get("slave_id", self.MODBUS_SLAVE_ID)
        self.locker_count = config.get("locker_count", 24)
        self._reader = None
        self._writer = None

    def _crc16(self, data: bytes) -> bytes:
        """Modbus RTU CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    def _build_frame(self, func: int, addr: int, data: int = 0) -> bytes:
        """Собрать Modbus RTU кадр"""
        payload = bytes([self.slave_id, func, (addr >> 8) & 0xFF, addr & 0xFF, (data >> 8) & 0xFF, data & 0xFF])
        return payload + self._crc16(payload)

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5.0
            )
            self._status = DeviceStatus.ONLINE
            self._last_ping = datetime.utcnow()
            return True
        except Exception as e:
            self._status = DeviceStatus.OFFLINE
            print(f"[Kerong {self.device_id}] Connect failed: {e}")
            return False

    async def disconnect(self):
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
            # Читаем регистр статуса контроллера (адрес 0x0000)
            frame = self._build_frame(self.FUNC_READ_HOLDING, 0x0000, 1)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(8), timeout=3.0)
            if len(resp) >= 5 and resp[1] == self.FUNC_READ_HOLDING:
                self._last_ping = datetime.utcnow()
                self._status = DeviceStatus.ONLINE
                return True
        except:
            pass
        self._status = DeviceStatus.OFFLINE
        return False

    async def open(self, credential: str = None, **kwargs) -> AccessResult:
        """Для Kerong open = открыть шкафчик по locker_id"""
        locker_id = kwargs.get("locker_id", kwargs.get("credential", "1"))
        success = await self.release_locker(str(locker_id))
        return AccessResult.GRANTED if success else AccessResult.ERROR

    async def close(self, **kwargs) -> bool:
        """Шкафчики Kerong сами закрываются механически"""
        return True

    async def release_locker(self, locker_id: str, **kwargs) -> bool:
        """Открыть конкретный шкафчик"""
        if not self._writer:
            return False
        try:
            addr = self.REG_OPEN_BASE + (int(locker_id) - 1)
            frame = self._build_frame(self.FUNC_WRITE_SINGLE, addr, 0x0001)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(8), timeout=3.0)
            if len(resp) >= 5 and resp[1] == self.FUNC_WRITE_SINGLE:
                await self._emit_event(HardwareEvent(
                    HWEventType.ENTRY, self.device_id,
                    details={"locker_id": locker_id, "action": "opened"}
                ))
                return True
        except Exception as e:
            print(f"[Kerong {self.device_id}] Release locker {locker_id} failed: {e}")
        return False

    async def get_locker_status(self, locker_id: str, **kwargs) -> dict:
        """Статус шкафчика: открыт/закрыт/занят"""
        if not self._writer:
            return {"error": "not connected"}
        try:
            addr = self.REG_STATUS_BASE + (int(locker_id) - 1)
            frame = self._build_frame(self.FUNC_READ_HOLDING, addr, 1)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(7), timeout=3.0)
            if len(resp) >= 5:
                status_byte = resp[3]
                return {
                    "locker_id": locker_id,
                    "is_closed": bool(status_byte & 0x01),
                    "is_occupied": bool(status_byte & 0x02),
                    "led_on": bool(status_byte & 0x04),
                    "alarm": bool(status_byte & 0x08),
                }
        except Exception as e:
            return {"error": str(e)}
        return {"error": "no response"}

    async def get_all_lockers_status(self) -> list[dict]:
        """Получить статус всех шкафчиков одним запросом"""
        if not self._writer:
            return []
        try:
            frame = self._build_frame(self.FUNC_READ_HOLDING, self.REG_STATUS_BASE, self.locker_count)
            self._writer.write(frame)
            resp_len = 5 + self.locker_count * 2
            resp = await asyncio.wait_for(self._reader.read(resp_len), timeout=5.0)
            if len(resp) >= 5 and resp[1] == self.FUNC_READ_HOLDING:
                results = []
                for i in range(self.locker_count):
                    byte_idx = 3 + i * 2
                    if byte_idx + 1 < len(resp):
                        status_byte = resp[byte_idx + 1]
                        results.append({
                            "locker_id": i + 1,
                            "is_closed": bool(status_byte & 0x01),
                            "is_occupied": bool(status_byte & 0x02),
                        })
                return results
        except Exception as e:
            print(f"[Kerong {self.device_id}] Bulk status failed: {e}")
        return []

    async def get_device_info(self) -> dict:
        return {
            "vendor": self.VENDOR,
            "model": self.config.get("model", "unknown"),
            "locker_count": self.locker_count,
            "slave_id": self.slave_id,
            "ip": self.host,
            "port": self.port,
            "protocol": "modbus_rtu_over_tcp",
            "status": self._status.value,
        }

    async def start_event_listener(self):
        """Kerong не шлёт события асинхронно — polling статуса"""
        while True:
            try:
                statuses = await self.get_all_lockers_status()
                await asyncio.sleep(5)
            except Exception:
                await asyncio.sleep(10)
                await self.connect()

    async def stop_event_listener(self):
        pass
