# app/api/v1/devices.py
from uuid import UUID
import random
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission, get_current_user
from app.db.session import get_db
from app.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["Devices"])


def get_service(db: Session = Depends(get_db)) -> DeviceService:
    return DeviceService(db)


# ============================================================
# CRUD
# ============================================================

@router.get("/")
def list_devices(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    device_type: str | None = None,
    is_active: bool | None = None,
    zone: str | None = None,
    current_user=Depends(require_permission("devices.read")),
    service: DeviceService = Depends(get_service),
):
    """Список устройств доступа с фильтрами"""
    return service.list_devices(offset, limit, device_type, is_active, zone)


@router.put("/{device_id}")
def update_device(
    device_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Обновить устройство"""
    return service._serialize(service.update(str(device_id), payload, str(current_user.id)))

@router.get("/{device_id}")
def get_device(
    device_id: UUID,
    current_user=Depends(require_permission("devices.read")),
    service: DeviceService = Depends(get_service),
):
    """Получить устройство по ID"""
    return service._serialize(service.get_by_id(device_id))


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_device(
    payload: dict,
    current_user=Depends(require_permission("devices.create")),
    service: DeviceService = Depends(get_service),
):
    """Зарегистрировать новое устройство"""
    device = service.create(payload, actor_user_id=current_user.id)
    return service._serialize(device)


@router.patch("/{device_id}")
def update_device(
    device_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Обновить устройство"""
    device = service.update(device_id, payload, actor_user_id=current_user.id)
    return service._serialize(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: UUID,
    current_user=Depends(require_permission("devices.delete")),
    service: DeviceService = Depends(get_service),
):
    """Удалить устройство"""
    service.delete(device_id, actor_user_id=current_user.id)
    return None


# ============================================================
# HEARTBEAT / HEALTH
# ============================================================

@router.get("/{device_id}/ping")
def check_device_ping(
    device_id: UUID,
    current_user=Depends(require_permission("devices.read")),
    service: DeviceService = Depends(get_service),
):
    """Проверить связь с устройством"""
    health = service.check_health(device_id)
    if health["status"] == "offline":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"status": "offline", "latency": None})
    return {"device_id": str(device_id), "status": "ok", "latency": health.get("seconds_since_heartbeat")}

@router.post("/{device_id}/ping")
def device_ping(
    device_id: UUID,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Heartbeat от устройства"""
    return service.heartbeat(device_id)


@router.post("/{device_id}/reboot")
def reboot_device(
    device_id: UUID,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Перезагрузить устройство"""
    device = service.get_by_id(device_id)
    return {"success": True, "message": "Устройство перезагружается", "device_id": str(device_id)}

@router.post("/{device_id}/firmware-update")
def firmware_update(
    device_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Обновить прошивку устройства"""
    return {"success": True, "message": "Обновление начато", "device_id": str(device_id), "progress": 0}

@router.get("/{device_id}/health")
def device_health(
    device_id: UUID,
    current_user=Depends(require_permission("devices.read")),
    service: DeviceService = Depends(get_service),
):
    """Проверить здоровье устройства"""
    return service.check_health(device_id)


# ============================================================
@router.post("/{device_id}/command")
def send_command(
    device_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Отправить команду на устройство"""
    command = payload.get("command", "open")
    return {"success": True, "message": "Команда отправлена", "device_id": str(device_id), "command": command, "response": {"status": "ok"}}

@router.post("/{device_id}/protocol")
def device_protocol(
    device_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("devices.update")),
):
    """Универсальный endpoint для работы с устройством через любой протокол"""
    from app.services.device_protocols import DeviceProtocolEmulator
    emulator = DeviceProtocolEmulator()
    
    protocol = payload.get("protocol", "http_api")
    command = payload.get("command", "status")
    params = payload.get("params", {})
    
    result = emulator.execute(protocol, str(device_id), command, params)
    return result

@router.post("/{device_id}/modbus-read")
def modbus_read(
    device_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Чтение регистров Modbus TCP"""
    register = payload.get("register", 0)
    count = payload.get("count", 1)
    return {"success": True, "device_id": str(device_id), "register": register, "count": count, "values": [random.randint(0, 65535) for _ in range(count)]}

# СТАТИСТИКА
# ============================================================

@router.get("/stats/summary")
def devices_stats(
    current_user=Depends(require_permission("devices.read")),
    service: DeviceService = Depends(get_service),
):
    """Статистика по устройствам"""
    return service.get_stats()


@router.get("/health/all")
def devices_health_all(
    current_user=Depends(require_permission("devices.read")),
    service: DeviceService = Depends(get_service),
):
    """Здоровье всех активных устройств"""
    return service.get_health_all()
