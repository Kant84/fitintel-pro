# app/api/v1/equipment.py — реестр фитнес-оборудования (E23)
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import require_roles, get_current_user
from app.db.session import get_db
from app.models.equipment import Equipment, MaintenanceRecord
from app.services.device_protocols import DeviceProtocolEmulator

router = APIRouter(prefix="/hardware", tags=["Hardware Equipment"])

ADMIN_ROLES = ("admin", "owner")
emulator = DeviceProtocolEmulator()


# ---------- схемы ----------

class EquipmentCreate(BaseModel):
    name: str
    type: str
    serial_number: str
    location: str | None = None
    vendor: str | None = None
    model: str | None = None
    protocol: str = "http_api"
    connection_string: str | None = None
    purchase_date: datetime | None = None
    warranty_until: datetime | None = None


class EquipmentUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    status: str | None = None
    warranty_until: datetime | None = None
    connection_string: str | None = None


class MaintenanceCreate(BaseModel):
    date: datetime
    description: str


class InventoryRequest(BaseModel):
    scanned_items: list[str]


class CommandRequest(BaseModel):
    command: str
    params: dict | None = None


class MqttPublishRequest(BaseModel):
    topic: str
    payload: dict | str


# ---------- helpers ----------

def _get(db: Session, equipment_id: UUID) -> Equipment:
    e = db.execute(select(Equipment).where(Equipment.id == equipment_id)).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")
    return e


def _warranty_info(e: Equipment) -> dict | None:
    if not e.warranty_until:
        return None
    now = datetime.now(timezone.utc)
    wu = e.warranty_until
    if wu.tzinfo is None:
        wu = wu.replace(tzinfo=timezone.utc)
    days = (wu - now).days
    return {
        "warranty_until": wu.isoformat(),
        "days_remaining": days,
        "is_expired": days < 0,
    }


def _serialize(e: Equipment) -> dict:
    return {
        "hardware_id": str(e.id),
        "name": e.name,
        "type": e.type,
        "serial_number": e.serial_number,
        "location": e.location,
        "vendor": e.vendor,
        "model": e.model,
        "status": e.status,
        "protocol": e.protocol,
        "connection_string": e.connection_string,
        "purchase_date": e.purchase_date.isoformat() if e.purchase_date else None,
        "warranty_info": _warranty_info(e),
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


# ---------- E23.1 / E23.2: регистрация ----------

@router.post("", status_code=201)
def create_equipment(
    data: EquipmentCreate,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E23.1: регистрация оборудования. E23.2: дубль serial -> 409"""
    existing = db.execute(
        select(Equipment).where(Equipment.serial_number == data.serial_number)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Серийный номер уже зарегистрирован")

    e = Equipment(id=uuid4(), **data.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return _serialize(e)


# ---------- E23.3: список ----------

@router.get("")
def list_equipment(
    type: str | None = None,
    status: str | None = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E23.3: список оборудования"""
    q = select(Equipment)
    if type:
        q = q.where(Equipment.type == type)
    if status:
        q = q.where(Equipment.status == status)
    rows = db.execute(q.order_by(Equipment.created_at)).scalars().all()
    return {"items": [_serialize(e) for e in rows], "count": len(rows)}


# ---------- E23.11: cron проверка гарантий (до /{id}!) ----------

@router.post("/warranty-check/run")
def warranty_check(
    days: int = Query(default=30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E23.11: cron — уведомление Admin об истечении гарантии через N дней"""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    rows = db.execute(
        select(Equipment).where(Equipment.warranty_until != None)
    ).scalars().all()

    notifications = []
    for e in rows:
        wu = e.warranty_until
        if wu.tzinfo is None:
            wu = wu.replace(tzinfo=timezone.utc)
        if now <= wu <= horizon:
            # здесь подключается реальная отправка Email
            notifications.append({
                "hardware_id": str(e.id),
                "name": e.name,
                "serial_number": e.serial_number,
                "days_remaining": (wu - now).days,
                "channel": "email",
                "to": "admin",
            })
    return {"notifications_sent": len(notifications), "notifications": notifications}


# ---------- E23.12: инвентаризация ----------

@router.post("/inventory")
def inventory(
    data: InventoryRequest,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E23.12: инвентаризация — расхождения между scanned_items и БД"""
    all_eq = db.execute(select(Equipment)).scalars().all()
    db_serials = {e.serial_number: e for e in all_eq}
    scanned = set(data.scanned_items)

    missing = [  # есть в БД, не отсканированы
        {"hardware_id": str(e.id), "serial_number": sn, "name": e.name, "location": e.location}
        for sn, e in db_serials.items() if sn not in scanned
    ]
    unknown = [sn for sn in scanned if sn not in db_serials]  # отсканированы, нет в БД
    matched = [sn for sn in scanned if sn in db_serials]

    return {
        "scanned": len(scanned),
        "matched": len(matched),
        "discrepancies": {"missing": missing, "unknown": unknown},
    }


# ---------- E23.4: по ID ----------

@router.get("/{equipment_id}")
def get_equipment(
    equipment_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E23.4: данные оборудования + warranty_info"""
    return _serialize(_get(db, equipment_id))


# ---------- E23.5: обновление ----------

@router.put("/{equipment_id}")
def update_equipment(
    equipment_id: UUID,
    data: EquipmentUpdate,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E23.5: обновление (location и др.)"""
    e = _get(db, equipment_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(e, field, value)
    db.commit()
    db.refresh(e)
    return _serialize(e)


# ---------- E23.6: удаление ----------

@router.delete("/{equipment_id}", status_code=204)
def delete_equipment(
    equipment_id: UUID,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E23.6: удаление оборудования"""
    e = _get(db, equipment_id)
    db.delete(e)
    db.commit()
    return Response(status_code=204)


# ---------- E23.7: статус ----------

@router.get("/{equipment_id}/status")
def equipment_status(
    equipment_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E23.7: статус online/offline/maintenance"""
    e = _get(db, equipment_id)
    return {"hardware_id": str(e.id), "status": e.status}


# ---------- E23.8 / E23.9: обслуживание ----------

@router.post("/{equipment_id}/maintenance")
def schedule_maintenance(
    equipment_id: UUID,
    data: MaintenanceCreate,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E23.8: запланировать обслуживание"""
    e = _get(db, equipment_id)
    rec = MaintenanceRecord(
        id=uuid4(), equipment_id=e.id,
        scheduled_date=data.date, description=data.description,
        status="scheduled",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {
        "maintenance_id": str(rec.id),
        "hardware_id": str(e.id),
        "scheduled_date": rec.scheduled_date.isoformat(),
        "description": rec.description,
        "status": rec.status,
        "message": "Обслуживание запланировано",
    }


@router.get("/{equipment_id}/maintenance-history")
def maintenance_history(
    equipment_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E23.9: история обслуживания"""
    e = _get(db, equipment_id)
    rows = db.execute(
        select(MaintenanceRecord)
        .where(MaintenanceRecord.equipment_id == e.id)
        .order_by(MaintenanceRecord.scheduled_date.desc())
    ).scalars().all()
    return {"items": [{
        "maintenance_id": str(r.id),
        "scheduled_date": r.scheduled_date.isoformat() if r.scheduled_date else None,
        "description": r.description,
        "status": r.status,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    } for r in rows]}


# ---------- E23.10: гарантия ----------

@router.get("/{equipment_id}/warranty")
def warranty(
    equipment_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E23.10: days_remaining + is_expired"""
    e = _get(db, equipment_id)
    info = _warranty_info(e)
    if not info:
        raise HTTPException(status_code=404, detail="Гарантийная информация отсутствует")
    return {"hardware_id": str(e.id), **info}


# ---------- E23.13: ЭРА / Modbus ----------

@router.get("/{equipment_id}/modbus-read")
def modbus_read(
    equipment_id: UUID,
    register: int = Query(default=0, ge=0),
    count: int = Query(default=4, ge=1, le=32),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """E23.13: чтение регистров ЭРА по Modbus"""
    e = _get(db, equipment_id)
    result = emulator.execute("modbus_tcp", str(e.id), "read",
                              {"register": register, "count": count})
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return {
        "hardware_id": str(e.id),
        "protocol": "modbus",
        "registers": result["values"],
        "register_start": register,
        "count": count,
        "timestamp": result["timestamp"],
    }


# ---------- E23.14: Kerong / HTTP ----------

@router.post("/{equipment_id}/command")
def send_command(
    equipment_id: UUID,
    data: CommandRequest,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E23.14: команда устройству по HTTP (Kerong: open -> замок открыт)"""
    e = _get(db, equipment_id)
    result = emulator.execute("http_api", str(e.id), data.command, data.params or {})
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    resp = {
        "hardware_id": str(e.id),
        "command": data.command,
        "success": True,
        "protocol_response": result,
    }
    if data.command == "open":
        resp["message"] = "Замок открыт"
        resp["lock_opened"] = True
    return resp


# ---------- E23.15: X1 / MQTT ----------

@router.post("/{equipment_id}/mqtt-publish")
def mqtt_publish(
    equipment_id: UUID,
    data: MqttPublishRequest,
    current_user=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """E23.15: публикация в MQTT-топик устройства X1"""
    e = _get(db, equipment_id)
    result = emulator.execute("mqtt", str(e.id), "publish",
                              {"topic": data.topic, "payload": data.payload})
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return {
        "hardware_id": str(e.id),
        "published": True,
        "topic": data.topic,
        "payload": data.payload,
        "timestamp": result["timestamp"],
    }
