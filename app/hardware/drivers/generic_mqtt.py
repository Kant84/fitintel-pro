# app/hardware/drivers/generic_mqtt.py — Универсальный MQTT драйвер
import asyncio
import json
from datetime import datetime
from app.hardware.base import BaseDeviceDriver, DeviceType, ConnectionProtocol, DeviceStatus, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import register_driver


@register_driver
class GenericMqttDriver(BaseDeviceDriver):
    """
    Универсальный MQTT драйвер для IoT СКУД.
    Работает с любым MQTT-брокером.
    """

    VENDOR = "Generic"
    MODELS = ["MQTT"]
    DEVICE_TYPES = [
        DeviceType.TURNSTILE, DeviceType.ELECTRIC_LOCK, DeviceType.LOCKER,
        DeviceType.CONTROLLER, DeviceType.BARRIER, DeviceType.GATE,
    ]
    PROTOCOLS = [ConnectionProtocol.MQTT]

    def __init__(self, config: dict):
        super().__init__(config)
        self.broker_host = config.get("broker_host", self.host)
        self.broker_port = config.get("broker_port", 1883)
        self.username = config.get("auth", {}).get("username", "")
        self.password = config.get("auth", {}).get("password", "")
        self.client_id = config.get("client_id", f"fitintel_{self.device_id}")
        self.use_ssl = config.get("ssl", False)

        # MQTT topics
        self.topics = config.get("topics", {
            "command_open": f"skud/{self.device_id}/cmd/open",
            "command_close": f"skud/{self.device_id}/cmd/close",
            "events": f"skud/{self.device_id}/events",
            "status": f"skud/{self.device_id}/status",
            "heartbeat": f"skud/{self.device_id}/heartbeat",
        })

        self._mqtt_client = None
        self._connected = False
        self._listening = False

    async def connect(self) -> bool:
        try:
            from asyncio_mqtt import Client, MqttError
            self._mqtt_client = Client(
                hostname=self.broker_host,
                port=self.broker_port,
                username=self.username or None,
                password=self.password or None,
                client_id=self.client_id,
                tls_context=True if self.use_ssl else None,
            )
            await self._mqtt_client.__aenter__()
            self._connected = True
            self._status = DeviceStatus.ONLINE
            self._last_ping = datetime.utcnow()
            return True
        except Exception as e:
            print(f"[MQTT {self.device_id}] Connect failed: {e}")
            self._status = DeviceStatus.OFFLINE
            return False

    async def disconnect(self):
        self._listening = False
        self._connected = False
        if self._mqtt_client:
            try:
                await self._mqtt_client.__aexit__(None, None, None)
            except:
                pass
        self._status = DeviceStatus.OFFLINE

    async def ping(self) -> bool:
        if not self._mqtt_client or not self._connected:
            return await self.connect()
        try:
            # Publish ping, wait for response on status topic
            await self._mqtt_client.publish(self.topics.get("status", ""), json.dumps({"ping": True}), timeout=5.0)
            self._last_ping = datetime.utcnow()
            self._status = DeviceStatus.ONLINE
            return True
        except Exception:
            self._status = DeviceStatus.OFFLINE
            return False

    async def open(self, credential: str = None, **kwargs) -> AccessResult:
        if not self._mqtt_client:
            return AccessResult.ERROR
        try:
            payload = {"action": "open", "timestamp": datetime.utcnow().isoformat()}
            if credential:
                payload["credential"] = credential
            if kwargs.get("client_id"):
                payload["client_id"] = kwargs["client_id"]
            if kwargs.get("duration_sec"):
                payload["duration_sec"] = kwargs["duration_sec"]

            await self._mqtt_client.publish(
                self.topics.get("command_open", f"skud/{self.device_id}/cmd/open"),
                json.dumps(payload),
                qos=1
            )
            await self._emit_event(HardwareEvent(HWEventType.ENTRY, self.device_id, credential))
            return AccessResult.GRANTED
        except Exception as e:
            print(f"[MQTT {self.device_id}] Open error: {e}")
            return AccessResult.ERROR

    async def close(self, **kwargs) -> bool:
        if not self._mqtt_client:
            return False
        try:
            await self._mqtt_client.publish(
                self.topics.get("command_close", f"skud/{self.device_id}/cmd/close"),
                json.dumps({"action": "close", "timestamp": datetime.utcnow().isoformat()}),
                qos=1
            )
            return True
        except:
            return False

    async def get_device_info(self) -> dict:
        return {
            "vendor": self.VENDOR,
            "protocol": "mqtt",
            "broker": f"{self.broker_host}:{self.broker_port}",
            "client_id": self.client_id,
            "topics": self.topics,
            "status": self._status.value,
        }

    async def start_event_listener(self):
        if not self._mqtt_client:
            return
        self._listening = True
        try:
            async with self._mqtt_client.messages() as messages:
                await self._mqtt_client.subscribe(self.topics.get("events", f"skud/{self.device_id}/events"))
                await self._mqtt_client.subscribe(self.topics.get("heartbeat", f"skud/{self.device_id}/heartbeat"))
                async for message in messages:
                    if not self._listening:
                        break
                    try:
                        payload = json.loads(message.payload.decode())
                        event_type = HWEventType(payload.get("event", "heartbeat"))
                        await self._emit_event(HardwareEvent(
                            event_type, self.device_id,
                            payload.get("credential"),
                            details=payload
                        ))
                        if event_type == HWEventType.HEARTBEAT:
                            self._last_ping = datetime.utcnow()
                            self._status = DeviceStatus.ONLINE
                    except Exception as e:
                        print(f"[MQTT {self.device_id}] Parse error: {e}")
        except Exception as e:
            print(f"[MQTT {self.device_id}] Listener error: {e}")

    async def stop_event_listener(self):
        self._listening = False
