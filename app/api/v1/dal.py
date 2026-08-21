"""E47: DAL — Device Abstraction Layer (ТЗ v3.2 §4.26, E15).

Плагиновая архитектура драйверов оборудования: репозиторий .fnp
пакетов, установка/включение/обновление/удаление драйверов,
автообнаружение устройств, выполнение команд, Driver SDK.
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:  # pragma: no cover
    try:
        from app.core.database import get_db
    except ImportError:
        from app.database import get_db

from app.api.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/dal", tags=["dal"])

_FMT = "%Y-%m-%d %H:%M:%S"

# Эмуляция репозитория .fnp-пакетов (в проде — внешний registry)
REPOSITORY = [
    {"package_name": "fnp.atol-kkt", "latest_version": "3.2.1", "device_type": "kkt",
     "description": "Драйвер ККТ АТОЛ (ФФД 1.2)",
     "discovery": [{"name": "АТОЛ 30Ф", "connection_string": "usb://atol/0"}]},
    {"package_name": "fnp.shtrih-kkt", "latest_version": "2.3.0", "device_type": "kkt",
     "description": "Драйвер ККТ Штрих-М",
     "discovery": [{"name": "Штрих-ON-LINE", "connection_string": "com://3"}]},
    {"package_name": "fnp.mercury-scale", "latest_version": "1.8.0", "device_type": "scale",
     "description": "Весы Mercury M-ER",
     "discovery": [{"name": "Mercury M-ER 326", "connection_string": "com://4"}]},
    {"package_name": "fnp.hikvision-face", "latest_version": "5.1.0", "device_type": "turnstile",
     "description": "Face ID терминал Hikvision (турникет)",
     "discovery": [{"name": "Hikvision DS-K1T671", "connection_string": "onvif://192.168.1.70"}]},
    {"package_name": "fnp.zebra-scanner", "latest_version": "1.2.0", "device_type": "scanner",
     "description": "Сканер штрих-кодов Zebra", "discovery": []},
]

_SDK_DOCS = {
    "package_format": ".fnp (zip: manifest.json + driver.py)",
    "manifest_fields": ["package_name", "version", "device_type", "description", "discovery"],
    "driver_methods": ["connect(connection_string)", "disconnect()", "ping()",
                       "execute(command, params)", "discover()"],
    "device_types": ["kkt", "scale", "scanner", "turnstile", "terminal"],
    "lifecycle": ["installed", "enabled", "disabled", "error"],
}


def _fmt(dt):
    return dt.strftime(_FMT)


def _cols(db, table):
    rows = db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _insert(db, table, data):
    cols = _cols(db, table)
    d = {k: v for k, v in data.items() if k in cols}
    names = ", ".join(d.keys())
    params = ", ".join(":" + k for k in d.keys())
    db.execute(text(f"INSERT INTO {table} ({names}) VALUES ({params})"), d)


def _get_driver(db, driver_id):
    row = db.execute(
        text("SELECT * FROM dal_drivers WHERE id=:i"), {"i": driver_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Драйвер не найден")
    return dict(row)


def _repo_package(name):
    for p in REPOSITORY:
        if p["package_name"] == name:
            return p
    return None


def _get_device(db, device_id):
    row = db.execute(
        text("SELECT * FROM dal_devices WHERE id=:i"), {"i": device_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return dict(row)


class InstallRequest(BaseModel):
    package_name: str
    version: Optional[str] = None


class DeviceAdd(BaseModel):
    driver_id: str
    name: str
    connection_string: str


class DiscoverRequest(BaseModel):
    driver_id: str


class CommandRequest(BaseModel):
    command: str
    params: Optional[dict] = None


@router.get("/repository")
def list_repository(user=Depends(get_current_user)):
    return REPOSITORY


@router.get("/sdk")
def sdk_docs(user=Depends(get_current_user)):
    return _SDK_DOCS


@router.post("/drivers/install", status_code=201)
def install_driver(payload: InstallRequest, db: Session = Depends(get_db),
                   user=Depends(require_roles("admin"))):
    pkg = _repo_package(payload.package_name)
    if not pkg:
        raise HTTPException(status_code=404, detail="Пакет не найден в репозитории")
    dup = db.execute(
        text("SELECT id FROM dal_drivers WHERE package_name=:p"), {"p": payload.package_name}
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Драйвер уже установлен")
    did = str(uuid.uuid4())
    version = payload.version or pkg["latest_version"]
    _insert(db, "dal_drivers", {
        "id": did, "package_name": pkg["package_name"], "version": version,
        "device_type": pkg["device_type"], "status": "installed",
        "manifest": json.dumps(pkg, ensure_ascii=False), "source": "repository",
        "installed_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"driver_id": did, "package_name": pkg["package_name"], "version": version,
            "status": "installed", "message": "Драйвер установлен"}


@router.get("/drivers")
def list_drivers(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(text("SELECT * FROM dal_drivers ORDER BY installed_at")).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/drivers/{driver_id}")
def get_driver(driver_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    d = _get_driver(db, driver_id)
    if d.get("manifest"):
        d["manifest"] = json.loads(d["manifest"])
    return d


@router.post("/drivers/{driver_id}/enable")
def enable_driver(driver_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_driver(db, driver_id)
    db.execute(text("UPDATE dal_drivers SET status='enabled' WHERE id=:i"), {"i": driver_id})
    db.commit()
    return {"message": "Драйвер включён", "status": "enabled"}


@router.post("/drivers/{driver_id}/disable")
def disable_driver(driver_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_driver(db, driver_id)
    db.execute(text("UPDATE dal_drivers SET status='disabled' WHERE id=:i"), {"i": driver_id})
    db.commit()
    return {"message": "Драйвер выключен", "status": "disabled"}


@router.post("/drivers/{driver_id}/upgrade")
def upgrade_driver(driver_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    d = _get_driver(db, driver_id)
    pkg = _repo_package(d["package_name"])
    if not pkg:
        raise HTTPException(status_code=404, detail="Пакет не найден в репозитории")
    if d["version"] == pkg["latest_version"]:
        raise HTTPException(status_code=400, detail="Уже последняя версия")
    db.execute(
        text("UPDATE dal_drivers SET version=:v, manifest=:m WHERE id=:i"),
        {"v": pkg["latest_version"], "m": json.dumps(pkg, ensure_ascii=False), "i": driver_id},
    )
    db.commit()
    return {"message": "Драйвер обновлён", "old_version": d["version"],
            "version": pkg["latest_version"]}


@router.delete("/drivers/{driver_id}", status_code=204)
def delete_driver(driver_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_driver(db, driver_id)
    db.execute(
        text("DELETE FROM dal_events WHERE device_id IN (SELECT id FROM dal_devices WHERE driver_id=:i)"),
        {"i": driver_id},
    )
    db.execute(text("DELETE FROM dal_devices WHERE driver_id=:i"), {"i": driver_id})
    db.execute(text("DELETE FROM dal_drivers WHERE id=:i"), {"i": driver_id})
    db.commit()
    return None


@router.post("/devices/discover")
def discover_devices(payload: DiscoverRequest, db: Session = Depends(get_db),
                     user=Depends(require_roles("admin"))):
    d = _get_driver(db, payload.driver_id)
    if d["status"] != "enabled":
        raise HTTPException(status_code=400, detail="Драйвер не активен")
    pkg = _repo_package(d["package_name"]) or {}
    found, added = 0, []
    for dev in pkg.get("discovery", []):
        found += 1
        dup = db.execute(
            text("SELECT id FROM dal_devices WHERE driver_id=:d AND connection_string=:c"),
            {"d": payload.driver_id, "c": dev["connection_string"]},
        ).fetchone()
        if not dup:
            _insert(db, "dal_devices", {
                "id": str(uuid.uuid4()), "driver_id": payload.driver_id,
                "name": dev["name"], "connection_string": dev["connection_string"],
                "status": "online", "last_seen": _fmt(datetime.now()),
                "created_at": _fmt(datetime.now()),
            })
            added.append(dev["name"])
    db.commit()
    return {"found": found, "added": len(added), "added_devices": added,
            "message": "Автообнаружение завершено"}


@router.get("/devices")
def list_devices(driver_id: Optional[str] = Query(None), db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    q = "SELECT * FROM dal_devices WHERE 1=1"
    params = {}
    if driver_id:
        q += " AND driver_id=:d"
        params["d"] = driver_id
    q += " ORDER BY created_at"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/devices", status_code=201)
def add_device(payload: DeviceAdd, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    d = _get_driver(db, payload.driver_id)
    if d["status"] != "enabled":
        raise HTTPException(status_code=400, detail="Драйвер не активен")
    did = str(uuid.uuid4())
    _insert(db, "dal_devices", {
        "id": did, "driver_id": payload.driver_id, "name": payload.name,
        "connection_string": payload.connection_string, "status": "online",
        "last_seen": _fmt(datetime.now()), "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"device_id": did, "message": "Устройство добавлено"}


@router.post("/devices/{device_id}/ping")
def ping_device(device_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_device(db, device_id)
    now = _fmt(datetime.now())
    db.execute(
        text("UPDATE dal_devices SET status='online', last_seen=:t WHERE id=:i"),
        {"t": now, "i": device_id},
    )
    _insert(db, "dal_events", {
        "id": str(uuid.uuid4()), "device_id": device_id, "event_type": "ping",
        "payload": "ok", "created_at": now,
    })
    db.commit()
    return {"device_id": device_id, "status": "online", "last_seen": now}


@router.post("/devices/{device_id}/command")
def device_command(device_id: str, payload: CommandRequest, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    dev = _get_device(db, device_id)
    if dev["status"] != "online":
        raise HTTPException(status_code=400, detail="Устройство недоступно")
    result = {"ok": True, "command": payload.command, "echo": payload.params or {}}
    _insert(db, "dal_events", {
        "id": str(uuid.uuid4()), "device_id": device_id, "event_type": "command",
        "payload": json.dumps(result, ensure_ascii=False), "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"device_id": device_id, "result": result}


@router.get("/events")
def list_events(device_id: Optional[str] = Query(None), db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    q = "SELECT * FROM dal_events WHERE 1=1"
    params = {}
    if device_id:
        q += " AND device_id=:d"
        params["d"] = device_id
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]
