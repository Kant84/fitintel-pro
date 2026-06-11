# app/api/v1/hardware.py — API для управления СКУД-устройствами
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import require_permission
from app.hardware.manager import DeviceManager
from app.hardware.registry import DriverRegistry

router = APIRouter(prefix="/hardware", tags=["Hardware"])


@router.get("/devices")
def list_devices(
    current_user=Depends(require_permission("devices.read")),
):
    """Список всех подключенных СКУД-устройств"""
    return {
        "items": DeviceManager.list_devices(),
        "count": len(DeviceManager.list_devices()),
    }


@router.get("/devices/{device_id}")
def get_device(
    device_id: str,
    current_user=Depends(require_permission("devices.read")),
):
    """Информация об устройстве"""
    device = DeviceManager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return device.to_dict()


@router.post("/devices/{device_id}/open")
async def open_device(
    device_id: str,
    credential: str = "",
    current_user=Depends(require_permission("devices.update")),
):
    """Открыть устройство (турникет/ворота/замок)"""
    result = await DeviceManager.open_device(device_id, credential=credential)
    return {"result": result.value, "device_id": device_id}


@router.post("/devices/{device_id}/close")
async def close_device(
    device_id: str,
    current_user=Depends(require_permission("devices.update")),
):
    """Закрыть устройство"""
    result = await DeviceManager.close_device(device_id)
    return {"result": "ok" if result else "failed", "device_id": device_id}


@router.post("/devices/{device_id}/ping")
async def ping_device(
    device_id: str,
    current_user=Depends(require_permission("devices.read")),
):
    """Проверить связь с устройством"""
    result = await DeviceManager.ping_device(device_id)
    return {"online": result, "device_id": device_id}


@router.get("/devices/{device_id}/info")
async def device_info(
    device_id: str,
    current_user=Depends(require_permission("devices.read")),
):
    """Подробная информация об устройстве"""
    device = DeviceManager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return await device.get_device_info()


# ── Шкафчики ──

@router.post("/devices/{device_id}/lockers/{locker_id}/release")
async def release_locker(
    device_id: str,
    locker_id: str,
    current_user=Depends(require_permission("devices.update")),
):
    """Открыть шкафчик"""
    result = await DeviceManager.release_locker(device_id, locker_id)
    return {"released": result, "device_id": device_id, "locker_id": locker_id}


@router.get("/devices/{device_id}/lockers/{locker_id}/status")
async def locker_status(
    device_id: str,
    locker_id: str,
    current_user=Depends(require_permission("devices.read")),
):
    """Статус шкафчика"""
    return await DeviceManager.get_locker_status(device_id, locker_id)


# ── Управление конфигурацией ──

@router.get("/drivers")
def list_drivers(
    current_user=Depends(require_permission("devices.read")),
):
    """Список всех доступных драйверов"""
    return {
        "items": DeviceManager.get_available_drivers(),
    }


@router.post("/devices")
async def add_device(
    config: dict,
    current_user=Depends(require_permission("devices.create")),
):
    """Динамически добавить устройство без перезапуска"""
    success = await DeviceManager.add_device(config)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось добавить устройство (драйвер не найден)")
    return {"status": "added", "device_id": config.get("device_id")}


@router.delete("/devices/{device_id}")
async def remove_device(
    device_id: str,
    current_user=Depends(require_permission("devices.delete")),
):
    """Удалить устройство"""
    await DeviceManager.remove_device(device_id)
    return {"status": "removed", "device_id": device_id}
