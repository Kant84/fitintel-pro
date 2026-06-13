# app/api/v1/devices.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("/")
def list_devices(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user=Depends(require_permission("devices.read")),
    db: Session = Depends(get_db),
):
    """Список устройств доступа (турникеты, шкафчики, считыватели)"""
    from app.models.device import Device
    from app.db.base import uuid_type
    devices = db.query(Device).offset(offset).limit(limit).all()
    return {
        "items": [{"id": str(d.id), "name": d.name, "device_type": d.device_type,
                   "location": d.location, "is_active": d.is_active,
                   "last_ping": d.last_ping.isoformat() if d.last_ping else None} for d in devices],
        "count": db.query(Device).count(),
    }


@router.get("/{device_id}")
def get_device(
    device_id: UUID,
    current_user=Depends(require_permission("devices.read")),
    db: Session = Depends(get_db),
):
    """Получить устройство по ID"""
    from app.models.device import Device
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return {"id": str(device.id), "name": device.name, "device_type": device.device_type,
            "location": device.location, "is_active": device.is_active,
            "config": device.config, "last_ping": device.last_ping.isoformat() if device.last_ping else None}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_device(
    payload: dict,
    current_user=Depends(require_permission("devices.create")),
    db: Session = Depends(get_db),
):
    """Зарегистрировать новое устройство"""
    from app.models.device import Device
    from app.db.base import utc_now
    import uuid
    device = Device(
        id=uuid.uuid4(),
        name=payload["name"],
        device_type=payload["device_type"],
        location=payload.get("location"),
        config=payload.get("config", {}),
        is_active=payload.get("is_active", True),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(device)
    db.commit()
    return {"id": str(device.id), "name": device.name, "status": "created"}


@router.patch("/{device_id}")
def update_device(
    device_id: UUID,
    payload: dict,
    current_user=Depends(require_permission("devices.update")),
    db: Session = Depends(get_db),
):
    """Обновить устройство"""
    from app.models.device import Device
    from app.db.base import utc_now
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    for field in ["name", "location", "config", "is_active"]:
        if field in payload:
            setattr(device, field, payload[field])
    device.updated_at = utc_now()
    db.commit()
    return {"id": str(device.id), "status": "updated"}


@router.post("/{device_id}/ping")
def device_ping(
    device_id: UUID,
    current_user=Depends(require_permission("devices.update")),
    db: Session = Depends(get_db),
):
    """Heartbeat от устройства"""
    from app.models.device import Device
    from app.db.base import utc_now
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    device.last_ping = utc_now()
    db.commit()
    return {"id": str(device.id), "status": "ok", "timestamp": device.last_ping.isoformat()}
