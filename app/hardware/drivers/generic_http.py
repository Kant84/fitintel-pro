# app/hardware/drivers/generic_http.py — Универсальный HTTP API драйвер
import aiohttp
from datetime import datetime
from app.hardware.base import BaseDeviceDriver, DeviceType, ConnectionProtocol, DeviceStatus, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import register_driver


@register_driver
class GenericHttpDriver(BaseDeviceDriver):
    """
    Универсальный драйвер для любого СКУД с HTTP REST API.
    Настраивается через JSON-шаблоны команд.
    """

    VENDOR = "Generic"
    MODELS = ["HTTP-API"]
    DEVICE_TYPES = [
        DeviceType.TURNSTILE, DeviceType.LOCKER, DeviceType.ELECTRIC_LOCK,
        DeviceType.CONTROLLER, DeviceType.BARRIER, DeviceType.GATE,
    ]
    PROTOCOLS = [ConnectionProtocol.HTTP_API]

    def __init__(self, config: dict):
        super().__init__(config)
        self.port = config.get("port", 80)
        self.base_url = config.get("base_url", f"http://{self.host}:{self.port}")
        self.api_key = config.get("auth", {}).get("api_key", "")
        self.login = config.get("auth", {}).get("login", "")
        self.password = config.get("auth", {}).get("password", "")

        # Настраиваемые endpoints
        self.endpoints = config.get("endpoints", {
            "open": {"method": "POST", "path": "/api/open", "body": {}},
            "close": {"method": "POST", "path": "/api/close", "body": {}},
            "status": {"method": "GET", "path": "/api/status"},
            "info": {"method": "GET", "path": "/api/info"},
        })
        self._session: aiohttp.ClientSession | None = None

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        elif self.login and self.password:
            import base64
            h["Authorization"] = "Basic " + base64.b64encode(f"{self.login}:{self.password}".encode()).decode()
        return h

    async def _request(self, action: str, extra_body: dict = None) -> tuple[int, dict]:
        """Выполнить HTTP запрос по шаблону"""
        if not self._session:
            return 0, {}
        tmpl = self.endpoints.get(action, {})
        method = tmpl.get("method", "GET")
        path = tmpl.get("path", "/")
        body = {**(tmpl.get("body") or {}), **(extra_body or {})}
        url = f"{self.base_url}{path}"

        try:
            if method == "GET":
                async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status, (await resp.json() if resp.content_type == 'application/json' else {})
            elif method == "POST":
                async with self._session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status, (await resp.json() if resp.content_type == 'application/json' else {})
            elif method == "PUT":
                async with self._session.put(url, json=body, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status, (await resp.json() if resp.content_type == 'application/json' else {})
        except Exception as e:
            print(f"[GenericHTTP {self.device_id}] Request {action} failed: {e}")
            return 0, {}
        return 0, {}

    async def connect(self) -> bool:
        self._session = aiohttp.ClientSession(headers=self._headers())
        return await self.ping()

    async def disconnect(self):
        if self._session:
            await self._session.close()
        self._status = DeviceStatus.OFFLINE

    async def ping(self) -> bool:
        status, _ = await self._request("status")
        if status in (200, 401):
            self._status = DeviceStatus.ONLINE
            self._last_ping = datetime.utcnow()
            return True
        self._status = DeviceStatus.OFFLINE
        return False

    async def open(self, credential: str = None, **kwargs) -> AccessResult:
        body = {}
        if credential:
            body["credential"] = credential
        if kwargs.get("client_id"):
            body["client_id"] = kwargs["client_id"]
        body.update(kwargs.get("extra", {}))

        status, data = await self._request("open", body)
        if status == 200 and data.get("success", True):
            await self._emit_event(HardwareEvent(HWEventType.ENTRY, self.device_id, credential))
            return AccessResult.GRANTED
        elif status == 403:
            return AccessResult.DENIED
        elif status == 0:
            return AccessResult.TIMEOUT
        return AccessResult.ERROR

    async def close(self, **kwargs) -> bool:
        status, _ = await self._request("close", kwargs.get("extra", {}))
        return status == 200

    async def get_device_info(self) -> dict:
        status, data = await self._request("info")
        data["driver"] = "GenericHttpDriver"
        data["configured_endpoints"] = list(self.endpoints.keys())
        return data

    async def start_event_listener(self):
        """HTTP polling или WebSocket если поддерживается"""
        ws_url = self.endpoints.get("websocket", {}).get("path")
        if ws_url:
            await self._ws_listener(ws_url)
        else:
            while True:
                await self._request("status")
                await asyncio.sleep(30)

    async def _ws_listener(self, ws_path: str):
        import aiohttp
        while True:
            try:
                async with aiohttp.ClientSession(headers=self._headers()) as session:
                    async with session.ws_connect(f"{self.base_url}{ws_path}") as ws:
                        self._status = DeviceStatus.ONLINE
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                import json
                                data = json.loads(msg.data)
                                await self._emit_event(HardwareEvent(
                                    HWEventType(data.get("event", "heartbeat")),
                                    self.device_id,
                                    data.get("credential"),
                                    details=data
                                ))
            except Exception as e:
                print(f"[GenericHTTP {self.device_id}] WS: {e}")
                await asyncio.sleep(10)

    async def stop_event_listener(self):
        pass
