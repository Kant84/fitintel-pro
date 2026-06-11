# app/hardware/manager.py — Менеджер устройств СКУД
import asyncio
import yaml
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.hardware.base import BaseDeviceDriver, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import DriverRegistry


class DeviceManager:
    """
    Центральный менеджер всех подключенных СКУД-устройств.
    Загружает конфигурацию, создаёт драйверы, управляет жизненным циклом.
    """

    _instance = None
    _devices: dict[str, BaseDeviceDriver] = {}
    _configs: list[dict] = []
    _event_handlers: list = []
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls, config_path: Optional[str] = None):
        """Инициализация: загрузка конфигов, подключение устройств"""
        if cls._initialized:
            return

        mgr = cls()

        # 1. Автообнаружение драйверов
        DriverRegistry.auto_discover()

        # 2. Загрузка конфигурации устройств
        if config_path:
            mgr._load_config(config_path)
        else:
            # Пробуем стандартные пути
            for path in ["config/devices.yaml", "config/devices.json", "devices.yaml"]:
                if Path(path).exists():
                    mgr._load_config(path)
                    break

        # 3. Создание и подключение драйверов
        for cfg in mgr._configs:
            await mgr._create_device(cfg)

        # 4. Запуск слушателей событий
        for device in mgr._devices.values():
            asyncio.create_task(device.start_event_listener())

        cls._initialized = True
        print(f"[DeviceManager] Initialized: {len(mgr._devices)} devices")

    def _load_config(self, path: str):
        """Загрузить конфиг устройств из YAML/JSON"""
        p = Path(path)
        if not p.exists():
            return

        with open(p, "r", encoding="utf-8") as f:
            if p.suffix == ".yaml" or p.suffix == ".yml":
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        if isinstance(data, dict) and "devices" in data:
            self._configs = data["devices"]
        elif isinstance(data, list):
            self._configs = data

    async def _create_device(self, cfg: dict):
        """Создать драйвер для устройства по конфигу"""
        device_id = cfg.get("device_id", cfg.get("id", "unknown"))
        try:
            driver = DriverRegistry.create_driver(cfg)
            if driver:
                self._devices[device_id] = driver
                # Подписка на события от устройства
                driver.on_event(self._on_device_event)
                # Подключение
                connected = await driver.connect()
                print(f"  [DeviceManager] {device_id}: {'connected' if connected else 'offline'}")
            else:
                print(f"  [DeviceManager] {device_id}: NO DRIVER FOUND (vendor={cfg.get('vendor')}, model={cfg.get('model')}, protocol={cfg.get('protocol')})")
        except Exception as e:
            print(f"  [DeviceManager] {device_id}: ERROR - {e}")

    def _on_device_event(self, event: HardwareEvent):
        """Обработчик событий от всех устройств"""
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                print(f"[DeviceManager] Event handler error: {e}")

    @classmethod
    def on_event(cls, handler):
        """Подписаться на события от всех устройств"""
        cls._event_handlers.append(handler)

    @classmethod
    def get_device(cls, device_id: str) -> Optional[BaseDeviceDriver]:
        return cls._devices.get(device_id)

    @classmethod
    def list_devices(cls) -> list[dict]:
        return [d.to_dict() for d in cls._devices.values()]

    @classmethod
    async def open_device(cls, device_id: str, credential: str = None, **kwargs) -> AccessResult:
        device = cls._devices.get(device_id)
        if not device:
            return AccessResult.ERROR
        return await device.open(credential=credential, **kwargs)

    @classmethod
    async def close_device(cls, device_id: str, **kwargs) -> bool:
        device = cls._devices.get(device_id)
        if not device:
            return False
        return await device.close(**kwargs)

    @classmethod
    async def release_locker(cls, device_id: str, locker_id: str) -> bool:
        device = cls._devices.get(device_id)
        if not device:
            return False
        return await device.release_locker(locker_id)

    @classmethod
    async def get_locker_status(cls, device_id: str, locker_id: str) -> dict:
        device = cls._devices.get(device_id)
        if not device:
            return {"error": "device not found"}
        return await device.get_locker_status(locker_id)

    @classmethod
    async def ping_device(cls, device_id: str) -> bool:
        device = cls._devices.get(device_id)
        if not device:
            return False
        return await device.ping()

    @classmethod
    async def add_device(cls, config: dict) -> bool:
        """Динамически добавить устройство без перезапуска"""
        mgr = cls()
        device_id = config.get("device_id", config.get("id"))
        if device_id in cls._devices:
            return False
        mgr._configs.append(config)
        await mgr._create_device(config)
        if device_id in cls._devices:
            asyncio.create_task(cls._devices[device_id].start_event_listener())
            return True
        return False

    @classmethod
    async def remove_device(cls, device_id: str):
        """Удалить устройство"""
        device = cls._devices.pop(device_id, None)
        if device:
            await device.stop_event_listener()
            await device.disconnect()

    @classmethod
    def get_available_drivers(cls) -> list[dict]:
        """Список всех доступных драйверов"""
        return DriverRegistry.list_drivers()
