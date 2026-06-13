# app/api/v1/devices.py
from uuid import UUID
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

@router.post("/{device_id}/ping")
def device_ping(
    device_id: UUID,
    current_user=Depends(require_permission("devices.update")),
    service: DeviceService = Depends(get_service),
):
    """Heartbeat от устройства"""
    return service.heartbeat(device_id)


@router.get("/{device_id}/health")
def device_health(
    device_id: UUID,
    current_user=Depends(require_permission("devices.read")),
    service: DeviceService = Depends(get_service),
):
    """Проверить здоровье устройства"""
    return service.check_health(device_id)


# ============================================================
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
