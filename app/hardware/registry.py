# app/hardware/registry.py — Реестр и фабрика драйверов СКУД
from typing import Type, Optional
import importlib
import pkgutil
from app.hardware.base import BaseDeviceDriver


class DriverRegistry:
    """Реестр всех доступных драйверов устройств"""

    _drivers: dict[str, Type[BaseDeviceDriver]] = {}
    _by_vendor: dict[str, list[Type[BaseDeviceDriver]]] = {}

    @classmethod
    def register(cls, driver_class: Type[BaseDeviceDriver]):
        """Зарегистрировать драйвер"""
        name = driver_class.__name__
        cls._drivers[name] = driver_class

        vendor = driver_class.VENDOR.lower()
        if vendor not in cls._by_vendor:
            cls._by_vendor[vendor] = []
        cls._by_vendor[vendor].append(driver_class)

        print(f"  [HW] Registered driver: {name} (vendor={driver_class.VENDOR}, models={driver_class.MODELS})")
        return driver_class

    @classmethod
    def auto_discover(cls):
        """Автоматически найти и зарегистрировать все драйверы в папке drivers/"""
        try:
            from app.hardware import drivers
            for _, modname, _ in pkgutil.iter_modules(drivers.__path__):
                try:
                    module = importlib.import_module(f"app.hardware.drivers.{modname}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseDeviceDriver) and
                            attr is not BaseDeviceDriver and
                            attr.__name__ not in cls._drivers):
                            cls.register(attr)
                except Exception as e:
                    print(f"  [HW] Failed to load driver module {modname}: {e}")
        except ImportError:
            pass

    @classmethod
    def create_driver(cls, config: dict) -> Optional[BaseDeviceDriver]:
        """
        Создать драйвер по конфигурации.
        Определяет драйвер по vendor/model или явному driver_class.
        """
        # Явное указание драйвера
        driver_class_name = config.get("driver_class")
        if driver_class_name and driver_class_name in cls._drivers:
            return cls._drivers[driver_class_name](config)

        # Определение по vendor + model
        vendor = (config.get("vendor") or "").lower()
        model = (config.get("model") or "").upper()

        if vendor and model:
            for drv_class in cls._by_vendor.get(vendor, []):
                if model in [m.upper() for m in drv_class.MODELS]:
                    return drv_class(config)

        # Определение только по vendor (берём первый подходящий)
        if vendor and vendor in cls._by_vendor:
            return cls._by_vendor[vendor][0](config)

        # Generic-драйвер по протоколу
        protocol = config.get("protocol", "").lower()
        if protocol == "modbus_tcp":
            from app.hardware.drivers.generic_modbus import GenericModbusDriver
            return GenericModbusDriver(config)
        elif protocol == "http_api":
            from app.hardware.drivers.generic_http import GenericHttpDriver
            return GenericHttpDriver(config)
        elif protocol == "mqtt":
            from app.hardware.drivers.generic_mqtt import GenericMqttDriver
            return GenericMqttDriver(config)

        return None

    @classmethod
    def list_drivers(cls) -> list[dict]:
        """Список всех зарегистрированных драйверов"""
        result = []
        for name, drv_class in cls._drivers.items():
            result.append({
                "class": name,
                "vendor": drv_class.VENDOR,
                "models": drv_class.MODELS,
                "device_types": [dt.value for dt in drv_class.DEVICE_TYPES],
                "protocols": [p.value for p in drv_class.PROTOCOLS],
            })
        return result

    @classmethod
    def get_supported_vendors(cls) -> list[str]:
        return sorted(cls._by_vendor.keys())


def register_driver(driver_class: Type[BaseDeviceDriver]):
    """Декоратор для регистрации драйвера"""
    return DriverRegistry.register(driver_class)
