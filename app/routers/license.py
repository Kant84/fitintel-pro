# app/routers/license.py
"""
License API — лицензирование FitIntel Pro.
Legacy-эндпоинты (verify/limits/revoke/activations) сохранены как были.
E28.1–E28.15: status/activate/devices/renew/verify-signature + эмуляция license server.
Работает поверх существующей таблицы licenses (face_id) — схема адаптивная (raw SQL).
"""

import hashlib
import hmac
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.license_service import LicenseService
from app.api.dependencies import get_current_user as real_auth, require_roles

router = APIRouter(prefix="/api/v1/license", tags=["License"])

LICENSE_SECRET = os.getenv("LICENSE_SECRET", "fitintel-license-secret")
DEFAULT_GRACE_DAYS = 7
DEFAULT_OFFLINE_DAYS = 30


# ---------- Legacy-заглушки авторизации (используются старыми эндпоинтами, не трогаем) ----------
async def get_current_user(request: Request):
    class DummyUser:
        id = 1
        role = "admin"
        email = "sanakinandrej4@gmail.com"
    return DummyUser()


def require_role(allowed_roles: list):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user
    return role_checker


# ---------- Helpers E28 ----------
def _checksum(base: str) -> str:
    return hmac.new(LICENSE_SECRET.encode(), base.encode(), hashlib.sha256).hexdigest()[:4].upper()


def _validate_key(key: str) -> bool:
    parts = (key or "").split("-")
    if len(parts) != 3 or parts[0] != "FITI" or len(parts[1]) != 8 or len(parts[2]) != 4:
        return False
    return hmac.compare_digest(_checksum(parts[1]), parts[2].upper())


def _sign(key: str, expires_at: datetime, device_limit: int) -> str:
    data = f"{key}|{expires_at.strftime('%Y-%m-%dT%H:%M:%S')}|{device_limit}"
    return hmac.new(LICENSE_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()


def _cols(db: Session, table: str) -> set:
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    return {r[0] for r in rows}


def _insert(db: Session, table: str, data: dict):
    cols = _cols(db, table)
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    db.execute(text(f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join(':' + k for k in data)})"), data)


_LIC_WANT = ["id", "license_key", "license_type", "plan", "device_limit",
             "expires_at", "grace_days", "offline_days", "last_check", "signature"]


def _get_license(db: Session) -> Optional[dict]:
    cols = _cols(db, "licenses")
    sel = [c for c in _LIC_WANT if c in cols]
    row = db.execute(text(f"SELECT {', '.join(sel)} FROM licenses ORDER BY id LIMIT 1")).fetchone()
    return dict(zip(sel, row)) if row else None


def _new_id(db: Session, table: str):
    """id для таблицы с учётом типа колонки (uuid или integer)"""
    dt = db.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = 'id'"
    ), {"t": table}).scalar()
    if dt == "uuid":
        return str(uuid.uuid4())
    return db.execute(text(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}")).scalar()


def _new_license_id(db: Session):
    return _new_id(db, "licenses")


def _devices_used(db: Session, lic_ref: str) -> int:
    return db.execute(text(
        "SELECT COUNT(*) FROM license_devices WHERE license_ref = :r"
    ), {"r": lic_ref}).scalar()


class ActivateRequest(BaseModel):
    license_key: str
    device_id: str


class DeactivateDeviceRequest(BaseModel):
    device_id: str
    license_key: Optional[str] = None


class RenewRequest(BaseModel):
    license_key: str


class GenerateRequest(BaseModel):
    days: int = 365
    device_limit: int = 2
    plan: str = "pro"


@router.post("/generate")
def generate_key(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """Выдать лицензионный ключ (эмуляция license server, E28.15)"""
    base = uuid.uuid4().hex[:8].upper()
    key = f"FITI-{base}-{_checksum(base)}"
    now = datetime.now(timezone.utc)
    _insert(db, "license_keys", {
        "id": _new_id(db, "license_keys"), "license_key": key, "key": key, "plan": payload.plan,
        "days": payload.days, "device_limit": payload.device_limit, "used": False,
        "created_at": now, "updated_at": now,
    })
    db.commit()
    return {"license_key": key, "days": payload.days,
            "device_limit": payload.device_limit, "plan": payload.plan}


@router.get("/status")
def license_status(
    offline: bool = False,
    db: Session = Depends(get_db),
    user=Depends(real_auth),
):
    """E28.1/E28.2/E28.9/E28.10/E28.13/E28.14 — статус лицензии"""
    lic = _get_license(db)
    now = datetime.now(timezone.utc)
    if not lic:
        return JSONResponse(status_code=403, content={"valid": False, "error": "Лицензия не активирована"})

    grace_days = lic.get("grace_days")
    if grace_days is None:
        grace_days = DEFAULT_GRACE_DAYS
    offline_days = lic.get("offline_days") or DEFAULT_OFFLINE_DAYS
    expires_at = lic.get("expires_at")
    last_check = lic.get("last_check")
    plan = lic.get("license_type") or lic.get("plan") or "pro"

    # Offline-режим: проверяем давность последней онлайн-проверки
    if offline:
        if not last_check or (now - last_check).days > offline_days:
            return JSONResponse(status_code=403, content={
                "offline_valid": False,
                "error": "Требуется подключение для проверки лицензии",
            })
        return {"offline_valid": True, "last_check": last_check.isoformat(),
                "offline_days_limit": offline_days}

    used = _devices_used(db, str(lic["id"]))

    if expires_at and expires_at > now:
        return {"valid": True, "expires_at": expires_at.isoformat(), "plan": plan,
                "device_limit": lic.get("device_limit"), "devices_used": used}

    if grace_days == 0:
        return JSONResponse(status_code=403, content={
            "valid": False, "error": "Лицензия истекла",
            "expires_at": expires_at.isoformat() if expires_at else None,
        })

    remaining = (expires_at + timedelta(days=grace_days)) - now
    if remaining.total_seconds() > 0:
        left = math.ceil(remaining.total_seconds() / 86400)
        return {"valid": True, "warning": f"Лицензия истекла, осталось {left} дней",
                "expires_at": expires_at.isoformat(), "grace_period": True,
                "grace_days_left": left}

    return JSONResponse(status_code=403, content={
        "valid": False, "error": "Лицензия истекла, доступ заблокирован"})

@router.post("/activate")
def activate(
    payload: ActivateRequest,
    db: Session = Depends(get_db),
    user=Depends(real_auth),
):
    """E28.3/E28.4/E28.5/E28.15 — активация лицензии на устройстве"""
    if not _validate_key(payload.license_key):
        raise HTTPException(status_code=400, detail="Невалидный ключ лицензии")

    key_row = db.execute(text(
        "SELECT plan, days, device_limit FROM license_keys WHERE license_key = :k"
    ), {"k": payload.license_key}).fetchone()
    plan = key_row[0] if key_row else "pro"
    days = key_row[1] if key_row else 365
    device_limit = key_row[2] if key_row else 2

    now = datetime.now(timezone.utc)
    lic = _get_license(db)

    existing = db.execute(text(
        "SELECT id FROM license_devices WHERE device_id = :d"
    ), {"d": payload.device_id}).fetchone()
    if not existing and lic and _devices_used(db, str(lic["id"])) >= device_limit:
        raise HTTPException(status_code=403, detail="Лимит устройств исчерпан")

    expires = now + timedelta(days=days)
    sig = _sign(payload.license_key, expires, device_limit)

    if lic:
        cols = _cols(db, "licenses")
        updates = {"license_key": payload.license_key, "license_type": plan, "plan": plan,
                   "device_limit": device_limit, "expires_at": expires,
                   "grace_days": DEFAULT_GRACE_DAYS, "offline_days": DEFAULT_OFFLINE_DAYS,
                   "last_check": now, "signature": sig, "is_active": True,
                   "is_revoked": False, "status": "active", "updated_at": now}
        setparts, params = [], {"lid": lic["id"]}
        for col, val in updates.items():
            if col in cols:
                setparts.append(f"{col} = :{col}")
                params[col] = val
        db.execute(text(f"UPDATE licenses SET {', '.join(setparts)} WHERE id = :lid"), params)
        lic_ref = str(lic["id"])
    else:
        new_id = _new_license_id(db)
        _insert(db, "licenses", {
            "id": new_id, "license_key": payload.license_key,
            "owner_name": "FitIntel Club", "owner_email": "admin@fitintel.pro",
            "license_type": plan, "plan": plan, "device_limit": device_limit,
            "max_users": 100, "max_terminals": 5, "max_clients": 1000,
            "expires_at": expires, "grace_days": DEFAULT_GRACE_DAYS,
            "offline_days": DEFAULT_OFFLINE_DAYS, "last_check": now,
            "signature": sig, "is_active": True, "is_revoked": False,
            "status": "active", "created_at": now, "updated_at": now,
        })
        lic_ref = str(new_id)

    if existing:
        db.execute(text(
            "UPDATE license_devices SET last_seen = :n WHERE device_id = :d"
        ), {"n": now, "d": payload.device_id})
    else:
        _insert(db, "license_devices", {
            "id": str(uuid.uuid4()), "license_ref": lic_ref,
            "device_id": payload.device_id, "last_seen": now,
            "created_at": now, "updated_at": now,
        })
    db.execute(text("UPDATE license_keys SET used = true WHERE license_key = :k"),
               {"k": payload.license_key})
    db.commit()
    return {"activated": True, "device_limit": device_limit,
            "expires_at": expires.isoformat(), "plan": plan,
            "server_confirmed": True, "license_server": "confirmed"}


@router.post("/deactivate-device")
def deactivate_device(
    payload: DeactivateDeviceRequest,
    db: Session = Depends(get_db),
    user=Depends(real_auth),
):
    """E28.6 — деактивация устройства, слот освобождается"""
    row = db.execute(text(
        "SELECT id FROM license_devices WHERE device_id = :d"
    ), {"d": payload.device_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Активация не найдена")
    db.execute(text("DELETE FROM license_devices WHERE device_id = :d"),
               {"d": payload.device_id})
    db.commit()
    return {"status": "deactivated", "deactivated": True,
            "device_id": payload.device_id, "slot_freed": True}


@router.get("/devices")
def list_devices(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E28.7 — список активных устройств"""
    rows = db.execute(text(
        "SELECT device_id, last_seen, created_at FROM license_devices ORDER BY created_at"
    )).fetchall()
    devices = [{
        "device_id": r[0],
        "last_seen": r[1].isoformat() if r[1] else None,
        "activated_at": r[2].isoformat() if r[2] else None,
    } for r in rows]
    return {"devices": devices, "count": len(devices)}


@router.post("/renew")
def renew(
    payload: RenewRequest,
    db: Session = Depends(get_db),
    user=Depends(real_auth),
):
    """E28.8 — продление лицензии новым ключом"""
    if not _validate_key(payload.license_key):
        raise HTTPException(status_code=400, detail="Невалидный ключ лицензии")
    lic = _get_license(db)
    if not lic:
        raise HTTPException(status_code=404, detail="Лицензия не активирована")
    key_row = db.execute(text(
        "SELECT days FROM license_keys WHERE license_key = :k"
    ), {"k": payload.license_key}).fetchone()
    days = key_row[0] if key_row else 365
    now = datetime.now(timezone.utc)
    base = max(now, lic["expires_at"]) if lic.get("expires_at") else now
    new_exp = base + timedelta(days=days)
    sig = _sign(payload.license_key, new_exp, lic.get("device_limit") or 2)

    cols = _cols(db, "licenses")
    updates = {"license_key": payload.license_key, "expires_at": new_exp,
               "grace_days": DEFAULT_GRACE_DAYS, "last_check": now,
               "signature": sig, "is_active": True, "is_revoked": False,
               "status": "active", "updated_at": now}
    setparts, params = [], {"lid": lic["id"]}
    for col, val in updates.items():
        if col in cols:
            setparts.append(f"{col} = :{col}")
            params[col] = val
    db.execute(text(f"UPDATE licenses SET {', '.join(setparts)} WHERE id = :lid"), params)
    db.execute(text("UPDATE license_keys SET used = true WHERE license_key = :k"),
               {"k": payload.license_key})
    db.commit()
    return {"renewed": True, "expires_at": new_exp.isoformat(), "expires_updated": True}


@router.get("/verify-signature")
def verify_signature(
    db: Session = Depends(get_db),
    user=Depends(real_auth),
):
    """E28.11/E28.12 — проверка подписи лицензии"""
    lic = _get_license(db)
    if not lic:
        raise HTTPException(status_code=404, detail="Лицензия не активирована")
    expected = _sign(lic["license_key"], lic["expires_at"], lic.get("device_limit") or 2)
    if lic.get("signature") and hmac.compare_digest(expected, lic["signature"]):
        return {"signature_valid": True}
    return JSONResponse(status_code=403, content={
        "signature_valid": False, "error": "Подпись лицензии невалидна"})


# ============================ LEGACY (не трогаем) ============================

class LicenseVerifyRequest(BaseModel):
    license_key: str
    device_id: str


@router.post("/verify")
async def verify_license(request: LicenseVerifyRequest, db: Session = Depends(get_db)):
    service = LicenseService(db)
    valid, message, info = service.verify_license(request.license_key, request.device_id)
    return {"valid": valid, "message": message, "info": info}


@router.get("/limits")
async def check_limits(license_key: str, db: Session = Depends(get_db),
                       current_user=Depends(require_role(["admin"]))):
    service = LicenseService(db)
    return service.check_system_limits(license_key)


@router.post("/revoke")
async def revoke_license(license_key: str, db: Session = Depends(get_db),
                         current_user=Depends(require_role(["admin"]))):
    service = LicenseService(db)
    success = service.revoke_license(license_key)
    if not success:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    return {"status": "revoked", "license_key": license_key}


@router.get("/{license_key}/activations")
async def get_activations(license_key: str, db: Session = Depends(get_db),
                          current_user=Depends(require_role(["admin"]))):
    from app.models.face_id import License
    license_obj = db.query(License).filter(License.license_key == license_key).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    return license_obj.activations
