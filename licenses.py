from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
import json

from app.database import get_db
from app.models import License
from app.schemas import (
    LicenseCreate, LicenseResponse,
    LicenseActivateRequest, LicenseActivateResponse,
    LicenseCheckRequest, LicenseCheckResponse,
    ErrorResponse
)
from app.schemas.enums import LicenseStatus
from app.core.auth import get_current_user, require_permission
from app.core.audit import log_action
from app.core.crypto import generate_license_key, sign_license, verify_license_signature

router = APIRouter(prefix="/licenses", tags=["Лицензирование (E14)"])


@router.post("", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
@require_permission("licenses.create")
async def create_license(
    license_data: LicenseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E14.12-E14.15 — Генерация лицензии с Ed25519 подписью
    """
    # Проверяем, не существует ли уже лицензия для этого HWID
    existing = db.query(License).filter(License.hwid == license_data.hwid).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": f"Лицензия для устройства {license_data.hwid} уже существует",
                "code": "LICENSE_EXISTS",
                "field": "hwid",
                "suggestion": "Используйте обновление существующей лицензии или деактивируйте старую"
            }
        )

    # Генерируем ключ и подпись
    license_key = generate_license_key()

    license_payload = {
        "club_name": license_data.club_name,
        "hwid": license_data.hwid,
        "modules": license_data.modules,
        "max_clients": license_data.max_clients,
        "max_cameras": license_data.max_cameras,
        "issued_at": license_data.issued_at.isoformat(),
        "expires_at": license_data.expires_at.isoformat()
    }

    signature = sign_license(json.dumps(license_payload, sort_keys=True))

    db_license = License(
        club_name=license_data.club_name,
        hwid=license_data.hwid,
        license_key=license_key,
        status=LicenseStatus.ACTIVE,
        modules=license_data.modules,
        max_clients=license_data.max_clients,
        max_cameras=license_data.max_cameras,
        issued_at=license_data.issued_at,
        expires_at=license_data.expires_at,
        signature=signature
    )
    db.add(db_license)
    db.commit()
    db.refresh(db_license)

    log_action(
        db=db,
        user_id=current_user.id,
        action="license_created",
        entity_type="license",
        entity_id=db_license.id,
        details={
            "club": license_data.club_name,
            "hwid": license_data.hwid,
            "modules": license_data.modules
        }
    )

    return db_license


@router.get("", response_model=List[LicenseResponse])
@require_permission("licenses.read")
async def list_licenses(
    status: Optional[LicenseStatus] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E14 — Список лицензий
    """
    query = db.query(License)
    if status:
        query = query.filter(License.status == status.value)

    licenses = query.order_by(License.created_at.desc()).all()
    return licenses


@router.get("/{license_id}", response_model=LicenseResponse)
@require_permission("licenses.read")
async def get_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E14 — Получить лицензию по ID
    """
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Лицензия #{license_id} не найдена",
                "code": "LICENSE_NOT_FOUND",
                "suggestion": "Проверьте ID лицензии или сгенерируйте новую"
            }
        )
    return license


@router.post("/activate", response_model=LicenseActivateResponse)
async def activate_license(
    activate_data: LicenseActivateRequest,
    db: Session = Depends(get_db)
):
    """
    E14.1, E14.6, E14.8-E14.9 — Активация лицензии на устройстве
    Проверка HWID, подписи, срока
    """
    license = db.query(License).filter(License.license_key == activate_data.license_key).first()

    if not license:
        return LicenseActivateResponse(
            success=False,
            message="Лицензионный ключ не найден",
            modules=None,
            expires_at=None
        )

    # Проверка HWID (E14.1)
    if license.hwid != activate_data.hwid:
        return LicenseActivateResponse(
            success=False,
            message="Лицензия привязана к другому устройству. HWID не совпадает",
            modules=None,
            expires_at=None
        )

    # Проверка подписи (E14.2)
    license_payload = {
        "club_name": license.club_name,
        "hwid": license.hwid,
        "modules": license.modules,
        "max_clients": license.max_clients,
        "max_cameras": license.max_cameras,
        "issued_at": license.issued_at.isoformat(),
        "expires_at": license.expires_at.isoformat()
    }

    if not verify_license_signature(json.dumps(license_payload, sort_keys=True), license.signature):
        return LicenseActivateResponse(
            success=False,
            message="Подпись лицензии невалидна. Файл повреждён или изменён",
            modules=None,
            expires_at=None
        )

    # Проверка срока (E14.4-E14.5)
    if license.expires_at < date.today():
        license.status = LicenseStatus.EXPIRED
        db.commit()
        return LicenseActivateResponse(
            success=False,
            message=f"Срок действия лицензии истёк ({license.expires_at})",
            modules=None,
            expires_at=license.expires_at
        )

    # Проверка статуса
    if license.status == LicenseStatus.REVOKED:
        return LicenseActivateResponse(
            success=False,
            message="Лицензия отозвана",
            modules=None,
            expires_at=None
        )

    # Успешная активация
    license.status = LicenseStatus.ACTIVE
    db.commit()

    return LicenseActivateResponse(
        success=True,
        message="Лицензия активирована",
        modules=license.modules,
        expires_at=license.expires_at
    )


@router.post("/check", response_model=LicenseCheckResponse)
async def check_license(
    check_data: LicenseCheckRequest,
    db: Session = Depends(get_db)
):
    """
    E14.8-E14.9 — Проверка статуса лицензии (online/offline)
    """
    license = db.query(License).filter(License.license_key == check_data.license_key).first()

    if not license:
        return LicenseCheckResponse(
            valid=False,
            status=LicenseStatus.REVOKED,
            modules=[],
            expires_at=date.today(),
            days_remaining=0
        )

    # Проверка HWID
    if license.hwid != check_data.hwid:
        return LicenseCheckResponse(
            valid=False,
            status=LicenseStatus.REVOKED,
            modules=[],
            expires_at=license.expires_at,
            days_remaining=0
        )

    days_remaining = (license.expires_at - date.today()).days

    if days_remaining < 0:
        license.status = LicenseStatus.EXPIRED
        db.commit()
        return LicenseCheckResponse(
            valid=False,
            status=LicenseStatus.EXPIRED,
            modules=[],
            expires_at=license.expires_at,
            days_remaining=0
        )

    return LicenseCheckResponse(
        valid=True,
        status=license.status,
        modules=license.modules,
        expires_at=license.expires_at,
        days_remaining=days_remaining
    )


@router.post("/{license_id}/deactivate")
@require_permission("licenses.deactivate")
async def deactivate_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E14.7 — Удалённая деактивация лицензии
    """
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Лицензия #{license_id} не найдена",
                "code": "LICENSE_NOT_FOUND",
                "suggestion": "Проверьте ID лицензии"
            }
        )

    license.status = LicenseStatus.REVOKED
    db.commit()

    log_action(
        db=db,
        user_id=current_user.id,
        action="license_deactivated",
        entity_type="license",
        entity_id=license_id,
        details={"club": license.club_name, "hwid": license.hwid}
    )

    return {
        "message": f"Лицензия для клуба «{license.club_name}» деактивирована",
        "license_id": license_id,
        "status": "revoked"
    }
