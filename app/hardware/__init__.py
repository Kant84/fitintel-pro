# Hardware Abstraction Layer (HAL) for SKUD devices
from app.hardware.registry import DriverRegistry, register_driver
from app.hardware.base import (
    BaseDeviceDriver, DeviceType, ConnectionProtocol,
    DeviceStatus, AccessResult, HWEventType, HardwareEvent,
)

# Auto-discover all drivers on import
DriverRegistry.auto_discover()
