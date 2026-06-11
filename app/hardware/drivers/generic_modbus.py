# app/hardware/drivers/generic_modbus.py — Универсальный Modbus TCP/RTU драйвер
import asyncio
from datetime import datetime
from app.hardware.base import BaseDeviceDriver, DeviceType, ConnectionProtocol, DeviceStatus, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import register_driver


@register_driver
class GenericModbusDriver(BaseDeviceDriver):
    """
    Универсальный Modbus драйвер для любого СКУД.
    Настраивается через map регистров.
    """

    VENDOR = "Generic"
    MODELS = ["MODBUS-TCP", "MODBUS-RTU"]
    DEVICE_TYPES = [
        DeviceType.TURNSTILE, DeviceType.ELECTRIC_LOCK, DeviceType.CONTROLLER,
        DeviceType.BARRIER, DeviceType.GATE, DeviceType.LOCKER,
    ]
    PROTOCOLS = [ConnectionProtocol.MODBUS_TCP, ConnectionProtocol.MODBUS_RTU]

    DEFAULT_PORT = 502

    FUNC_READ_COIL = 0x01
    FUNC_READ_DISCRETE = 0x02
    FUNC_READ_HOLDING = 0x03
    FUNC_READ_INPUT = 0x04
    FUNC_WRITE_SINGLE_COIL = 0x05
    FUNC_WRITE_SINGLE = 0x06
    FUNC_WRITE_MULTIPLE_COIL = 0x0F
    FUNC_WRITE_MULTIPLE = 0x10

    def __init__(self, config: dict):
        super().__init__(config)
        self.port = config.get("port", self.DEFAULT_PORT)
        self.slave_id = config.get("slave_id", 1)
        self.is_rtu_over_tcp = config.get("rtu_over_tcp", False)

        # Карта регистров — настраивается для каждого устройства
        self.register_map = config.get("register_map", {
            "open": {"type": "coil", "address": 0, "value_on": 1, "value_off": 0},
            "close": {"type": "coil", "address": 1, "value_on": 1, "value_off": 0},
            "status": {"type": "holding", "address": 0, "count": 1},
            "entry_sensor": {"type": "discrete", "address": 0, "count": 1},
            "exit_sensor": {"type": "discrete", "address": 1, "count": 1},
        })
        self._reader = None
        self._writer = None

    def _crc16(self, data: bytes) -> bytes:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
        return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    def _build_rtu_frame(self, func: int, addr: int, data: int) -> bytes:
        payload = bytes([self.slave_id, func, (addr >> 8) & 0xFF, addr & 0xFF, (data >> 8) & 0xFF, data & 0xFF])
        return payload + self._crc16(payload)

    def _build_tcp_frame(self, func: int, addr: int, data: int) -> bytes:
        """Modbus TCP (MBAP header + PDU)"""
        tid = 0x0001
        pdu = bytes([self.slave_id, func, (addr >> 8) & 0xFF, addr & 0xFF, (data >> 8) & 0xFF, data & 0xFF])
        mbap = bytes([(tid >> 8) & 0xFF, tid & 0xFF, 0x00, 0x00, 0x00, len(pdu)])
        return mbap + pdu

    def _build_frame(self, func: int, addr: int, data: int) -> bytes:
        if self.is_rtu_over_tcp:
            return self._build_rtu_frame(func, addr, data)
        return self._build_tcp_frame(func, addr, data)

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5.0)
            self._status = DeviceStatus.ONLINE
            self._last_ping = datetime.utcnow()
            return True
        except Exception as e:
            self._status = DeviceStatus.OFFLINE
            print(f"[Modbus {self.device_id}] Connect failed: {e}")
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
            reg = self.register_map.get("status", {"address": 0})
            frame = self._build_frame(self.FUNC_READ_HOLDING, reg["address"], 1)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(256), timeout=3.0)
            if len(resp) >= 5:
                self._last_ping = datetime.utcnow()
                self._status = DeviceStatus.ONLINE
                return True
        except:
            pass
        self._status = DeviceStatus.OFFLINE
        return False

    async def open(self, credential: str = None, **kwargs) -> AccessResult:
        if not self._writer:
            if not await self.connect():
                return AccessResult.ERROR
        try:
            reg = self.register_map.get("open", {"type": "coil", "address": 0, "value_on": 1})
            func = self.FUNC_WRITE_SINGLE_COIL if reg["type"] == "coil" else self.FUNC_WRITE_SINGLE
            value = reg.get("value_on", 1)
            if reg["type"] == "coil":
                value = 0xFF00 if value else 0x0000

            frame = self._build_frame(func, reg["address"], value)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(12), timeout=3.0)
            if len(resp) >= 5:
                await self._emit_event(HardwareEvent(HWEventType.ENTRY, self.device_id, credential))
                return AccessResult.GRANTED
            return AccessResult.ERROR
        except asyncio.TimeoutError:
            return AccessResult.TIMEOUT
        except Exception as e:
            print(f"[Modbus {self.device_id}] Open error: {e}")
            return AccessResult.ERROR

    async def close(self, **kwargs) -> bool:
        if not self._writer:
            return False
        try:
            reg = self.register_map.get("close", {"type": "coil", "address": 1, "value_on": 1})
            func = self.FUNC_WRITE_SINGLE_COIL if reg["type"] == "coil" else self.FUNC_WRITE_SINGLE
            value = 0xFF00 if reg.get("value_on") else 0x0000
            frame = self._build_frame(func, reg["address"], value)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(12), timeout=3.0)
            return len(resp) >= 5
        except:
            return False

    async def get_device_info(self) -> dict:
        return {
            "vendor": self.VENDOR,
            "protocol": "modbus_rtu_over_tcp" if self.is_rtu_over_tcp else "modbus_tcp",
            "slave_id": self.slave_id,
            "ip": self.host,
            "port": self.port,
            "register_map": self.register_map,
            "status": self._status.value,
        }

    async def start_event_listener(self):
        # Polling discrete inputs (sensors)
        entry_reg = self.register_map.get("entry_sensor")
        exit_reg = self.register_map.get("exit_sensor")
        if not entry_reg and not exit_reg:
            while True:
                await asyncio.sleep(60)
        while True:
            try:
                if entry_reg:
                    frame = self._build_frame(self.FUNC_READ_DISCRETE, entry_reg["address"], entry_reg.get("count", 1))
                    self._writer.write(frame)
                    resp = await asyncio.wait_for(self._reader.read(256), timeout=3.0)
                    if len(resp) >= 5 and resp[3] & 0x01:
                        await self._emit_event(HardwareEvent(HWEventType.ENTRY, self.device_id))
                if exit_reg:
                    frame = self._build_frame(self.FUNC_READ_DISCRETE, exit_reg["address"], exit_reg.get("count", 1))
                    self._writer.write(frame)
                    resp = await asyncio.wait_for(self._reader.read(256), timeout=3.0)
                    if len(resp) >= 5 and resp[3] & 0x01:
                        await self._emit_event(HardwareEvent(HWEventType.EXIT, self.device_id))
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(5)
                await self.connect()

    async def stop_event_listener(self):
        pass

    async def release_locker(self, locker_id: str, **kwargs) -> bool:
        """Если в register_map есть locker_N → открываем по адресу"""
        reg_key = f"locker_{locker_id}"
        if reg_key not in self.register_map:
            return False
        reg = self.register_map[reg_key]
        func = self.FUNC_WRITE_SINGLE_COIL if reg.get("type") == "coil" else self.FUNC_WRITE_SINGLE
        value = 0xFF00 if reg.get("value_on", 1) else 0x0000
        try:
            frame = self._build_frame(func, reg["address"], value)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(12), timeout=3.0)
            return len(resp) >= 5
        except:
            return False

    async def get_locker_status(self, locker_id: str, **kwargs) -> dict:
        reg_key = f"locker_{locker_id}_status"
        if reg_key not in self.register_map:
            return {"error": "not configured"}
        reg = self.register_map[reg_key]
        try:
            frame = self._build_frame(self.FUNC_READ_HOLDING, reg["address"], 1)
            self._writer.write(frame)
            resp = await asyncio.wait_for(self._reader.read(12), timeout=3.0)
            if len(resp) >= 5:
                return {"locker_id": locker_id, "status": resp[3], "raw": resp.hex()}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "no response"}
