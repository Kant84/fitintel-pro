# add_nfc_endpoints.py
with open('app/api/v1/hardware.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорты
old_imports = '''from app.api.dependencies import require_permission
from app.db.session import get_db'''
new_imports = '''from app.api.dependencies import require_permission
from app.db.session import get_db
from pydantic import BaseModel, Field'''

if old_imports in content:
    content = content.replace(old_imports, new_imports)

# Добавляем endpoint'ы в конец файла
new_endpoints = '''


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
'''

content = content + new_endpoints

with open('app/api/v1/hardware.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("NFC endpoint'ы добавлены!")
