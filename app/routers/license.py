from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.license_service import LicenseService

router = APIRouter(prefix="/api/v1/license", tags=["License"])

# Заглушка для текущего пользователя (заменить на реальную аутентификацию)
async def get_current_user(request: Request):
    class DummyUser:
        id = 1
        role = "admin"
        email = "admin@fitintel.pro"
    return DummyUser()

def require_role(allowed_roles: list):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user
    return role_checker

class LicenseVerifyRequest(BaseModel):
    license_key: str
    device_id: str

class LicenseCreateRequest(BaseModel):
    owner_name: str
    owner_email: str
    license_type: str = "standard"
    months: int = 12
    max_users: int = 100
    max_clients: int = 1000
    max_terminals: int = 5

class LicenseRevokeRequest(BaseModel):
    license_key: str

@router.post("/verify")
async def verify_license(request: LicenseVerifyRequest, db: Session = Depends(get_db)):
    service = LicenseService(db)
    valid, message, info = service.verify_license(request.license_key, request.device_id)
    return {"valid": valid, "message": message, "info": info}

@router.get("/limits")
async def check_limits(license_key: str, db: Session = Depends(get_db),
                       current_user = Depends(require_role(["admin"]))):
    service = LicenseService(db)
    return service.check_system_limits(license_key)

@router.post("/generate")
async def generate_license(request: LicenseCreateRequest, db: Session = Depends(get_db),
                           current_user = Depends(require_role(["admin"]))):
    service = LicenseService(db)
    key = service.generate_license(
        owner_name=request.owner_name, owner_email=request.owner_email,
        license_type=request.license_type, months=request.months,
        max_users=request.max_users, max_clients=request.max_clients,
        max_terminals=request.max_terminals
    )
    return {"license_key": key, "expires_in_months": request.months}

@router.post("/revoke")
async def revoke_license(request: LicenseRevokeRequest, db: Session = Depends(get_db),
                         current_user = Depends(require_role(["admin"]))):
    service = LicenseService(db)
    success = service.revoke_license(request.license_key)
    if not success:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    return {"status": "revoked", "license_key": request.license_key}

@router.post("/deactivate-device")
async def deactivate_device(license_key: str, device_id: str, db: Session = Depends(get_db),
                            current_user = Depends(require_role(["admin"]))):
    service = LicenseService(db)
    success = service.deactivate_device(license_key, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Активация не найдена")
    return {"status": "deactivated", "device_id": device_id}

@router.get("/{license_key}/activations")
async def get_activations(license_key: str, db: Session = Depends(get_db),
                          current_user = Depends(require_role(["admin"]))):
    from app.models.face_id import License
    license = db.query(License).filter(License.license_key == license_key).first()
    if not license:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    return license.activations