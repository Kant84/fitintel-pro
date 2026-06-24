# app/api/v1/hardware.py — API для управления СКУД-устройствами
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
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



# ==========================================================
# ACS ACR1252U NFC Reader/Writer
# ==========================================================

class NFCReadResponse(BaseModel):
    """Ответ чтения NFC карты"""
    success: bool
    uid: str | None = None
    device_id: str | None = None
    error: str | None = None


class NFCWriteRequest(BaseModel):
    """Запрос записи в MIFARE сектор"""
    device_id: str = Field(description="ID устройства (ACS ACR1252U)")
    sector: int = Field(ge=0, le=15, description="Номер сектора (0-15)")
    key_a: str = Field(min_length=12, max_length=12, description="Ключ A (12 hex)")
    data: str = Field(min_length=32, max_length=32, description="Данные (32 hex)")


class NFCWriteResponse(BaseModel):
    """Ответ записи в MIFARE"""
    success: bool
    sector: int
    device_id: str
    error: str | None = None


@router.post(
    "/nfc/read",
    response_model=NFCReadResponse,
    status_code=status.HTTP_200_OK,
)
async def nfc_read(
    device_id: str,
    current_user=Depends(require_permission("devices.read")),
):
    """
    Прочитать UID MIFARE карты через ACS ACR1252U.
    
    - Требует подключённого устройства
    - Возвращает UID карты (если приложена)
    """
    from app.hardware.manager import DeviceManager
    
    device = DeviceManager.get_device(device_id)
    if not device:
        return NFCReadResponse(
            success=False,
            error=f"Устройство {device_id} не найдено",
        )
    
    try:
        uid = await device.read_card()
        if uid:
            return NFCReadResponse(
                success=True,
                uid=uid,
                device_id=device_id,
            )
        else:
            return NFCReadResponse(
                success=False,
                error="Карта не обнаружена",
                device_id=device_id,
            )
    except Exception as e:
        return NFCReadResponse(
            success=False,
            error=str(e),
            device_id=device_id,
        )


@router.post(
    "/nfc/write",
    response_model=NFCWriteResponse,
    status_code=status.HTTP_200_OK,
)
async def nfc_write(
    payload: NFCWriteRequest,
    current_user=Depends(require_permission("devices.update")),
):
    """
    Записать данные в сектор MIFARE Classic через ACS ACR1252U.
    
    - Аутентификация с Key A
    - Запись 16 байт (32 hex символа)
    - Поддержка секторов 0-15
    """
    from app.hardware.manager import DeviceManager
    
    device = DeviceManager.get_device(payload.device_id)
    if not device:
        return NFCWriteResponse(
            success=False,
            sector=payload.sector,
            device_id=payload.device_id,
            error=f"Устройство {payload.device_id} не найдено",
        )
    
    try:
        result = await device.write_mifare_sector(
            sector=payload.sector,
            key_a=payload.key_a,
            data=payload.data,
        )
        return NFCWriteResponse(
            success=result,
            sector=payload.sector,
            device_id=payload.device_id,
        )
    except Exception as e:
        return NFCWriteResponse(
            success=False,
            sector=payload.sector,
            device_id=payload.device_id,
            error=str(e),
        )


@router.get(
    "/nfc/status",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def nfc_status(
    device_id: str,
    current_user=Depends(require_permission("devices.read")),
):
    """
    Получить статус ACS ACR1252U кард-ридера.
    """
    from app.hardware.manager import DeviceManager
    
    device = DeviceManager.get_device(device_id)
    if not device:
        return {
            "connected": False,
            "device_id": device_id,
            "error": "Устройство не найдено",
        }
    
    info = await device.get_device_info()
    return {
        "connected": info.get("connected", False),
        "device_id": device_id,
        "vendor": info.get("vendor"),
        "model": info.get("model"),
        "last_uid": info.get("last_uid"),
        "status": info.get("status"),
    }
