# app/hardware/drivers/x1.py — Драйвер для СКУД X1 (HTTP REST API)
import aiohttp
from datetime import datetime
from app.hardware.base import BaseDeviceDriver, DeviceType, ConnectionProtocol, DeviceStatus, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import register_driver


@register_driver
class X1Driver(BaseDeviceDriver):
    """Драйвер для контроллеров X1 (поддерживает HTTP REST API)"""

    VENDOR = "X1"
    MODELS = ["X1-LITE", "X1-PRO", "X1-MAX", "X1-NET", "X1-WIFI"]
    DEVICE_TYPES = [DeviceType.CONTROLLER, DeviceType.TURNSTILE, DeviceType.ELECTRIC_LOCK]
    PROTOCOLS = [ConnectionProtocol.HTTP_API, ConnectionProtocol.WEBSOCKET]

    DEFAULT_PORT = 8080

    def __init__(self, config: dict):
        super().__init__(config)
        self.port = config.get("port", self.DEFAULT_PORT)
        self.base_url = f"http://{self.host}:{self.port}"
        self.api_key = config.get("auth", {}).get("api_key", "")
        self._session: aiohttp.ClientSession | None = None

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def connect(self) -> bool:
        self._session = aiohttp.ClientSession(headers=self._headers())
        return await self.ping()

    async def disconnect(self):
        if self._session:
            await self._session.close()
        self._status = DeviceStatus.OFFLINE

    async def ping(self) -> bool:
        if not self._session:
            return False
        try:
            async with self._session.get(f"{self.base_url}/api/v1/status", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    self._status = DeviceStatus.ONLINE
                    self._last_ping = datetime.utcnow()
                    return True
        except Exception as e:
            print(f"[X1 {self.device_id}] Ping failed: {e}")
        self._status = DeviceStatus.OFFLINE
        return False

    async def open(self, credential: str = None, **kwargs) -> AccessResult:
        if not self._session:
            return AccessResult.ERROR
        try:
            payload = {"action": "open"}
            if credential:
                payload["credential"] = credential
            if kwargs.get("client_id"):
                payload["client_id"] = kwargs["client_id"]
            if kwargs.get("duration_sec"):
                payload["duration_sec"] = kwargs["duration_sec"]

            async with self._session.post(f"{self.base_url}/api/v1/relay/open", json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        await self._emit_event(HardwareEvent(
                            HWEventType.ENTRY, self.device_id, credential,
                            details={"relay": data.get("relay", 1)}
                        ))
                        return AccessResult.GRANTED
                    return AccessResult.DENIED
                elif resp.status == 403:
                    return AccessResult.INVALID_CREDENTIAL
                return AccessResult.ERROR
        except asyncio.TimeoutError:
            return AccessResult.TIMEOUT
        except Exception as e:
            print(f"[X1 {self.device_id}] Open error: {e}")
            return AccessResult.ERROR

    async def close(self, **kwargs) -> bool:
        if not self._session:
            return False
        try:
            async with self._session.post(f"{self.base_url}/api/v1/relay/close", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except:
            return False

    async def get_device_info(self) -> dict:
        if not self._session:
            return {"error": "not connected"}
        try:
            async with self._session.get(f"{self.base_url}/api/v1/info") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            return {"error": str(e)}
        return {}

    async def sync_credentials(self, credentials: list[dict]) -> bool:
        """Загрузить список ключей в X1"""
        if not self._session:
            return False
        try:
            async with self._session.post(f"{self.base_url}/api/v1/credentials/sync", json={"credentials": credentials}) as resp:
                return resp.status == 200
        except:
            return False

    async def start_event_listener(self):
        """WebSocket-прослушка событий X1"""
        import aiohttp
        while True:
            try:
                async with aiohttp.ClientSession(headers=self._headers()) as session:
                    async with session.ws_connect(f"ws://{self.host}:{self.port}/api/v1/events") as ws:
                        self._status = DeviceStatus.ONLINE
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                import json
                                data = json.loads(msg.data)
                                event_type = HWEventType(data.get("event", "heartbeat"))
                                await self._emit_event(HardwareEvent(
                                    event_type, self.device_id,
                                    data.get("credential"),
                                    details=data
                                ))
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                print(f"[X1 {self.device_id}] WS error: {e}")
                await asyncio.sleep(10)

    async def stop_event_listener(self):
        pass

    async def release_locker(self, locker_id: str, **kwargs) -> bool:
        """X1-PRO и X1-MAX поддерживают шкафчики через доп. модули"""
        if not self._session:
            return False
        try:
            async with self._session.post(f"{self.base_url}/api/v1/locker/{locker_id}/release") as resp:
                return resp.status == 200
        except:
            return False

    async def get_locker_status(self, locker_id: str, **kwargs) -> dict:
        if not self._session:
            return {}
        try:
            async with self._session.get(f"{self.base_url}/api/v1/locker/{locker_id}/status") as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            return {}
        return {}
