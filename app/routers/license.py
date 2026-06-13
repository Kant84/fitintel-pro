from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.license_service import LicenseService

router = APIRouter(prefix="/api/v1/license", tags=["License"])

async def get_current_user(request: Request):
    class DummyUser:
        id = 1
        role = "admin"
        email = "sanakinandrej4@gmail.com"
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

@router.post("/revoke")
async def revoke_license(license_key: str, db: Session = Depends(get_db),
                         current_user = Depends(require_role(["admin"]))):
    service = LicenseService(db)
    success = service.revoke_license(license_key)
    if not success:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    return {"status": "revoked", "license_key": license_key}

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