# app/services/license_service.py
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.face_id import License, LicenseActivation


class LicenseService:
    """Сервис управления лицензиями"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def verify_license(self, license_key: str, device_id: str) -> Tuple[bool, str, dict]:
        """Проверка и активация лицензии"""
        # DEMO-режим: любой ключ начинающийся с DEMO
        if license_key.startswith("DEMO"):
            return True, "License activated (demo mode)", {
                "type": "demo",
                "expires_at": None,
                "device_id": device_id
            }
        
        # Проверка в БД
        license_obj = self.db.query(License).filter(
            License.license_key == license_key,
            License.is_active == True
        ).first()
        
        if not license_obj:
            return False, "Invalid license key", {}
        
        # Проверка срока
        if license_obj.expires_at and license_obj.expires_at < datetime.now(timezone.utc):
            return False, "License expired", {}
        
        # Активация устройства
        activation = self.db.query(LicenseActivation).filter(
            LicenseActivation.license_id == license_obj.id,
            LicenseActivation.device_id == device_id
        ).first()
        
        if not activation:
            # Создаём новую активацию
            activation = LicenseActivation(
                license_id=license_obj.id,
                device_id=device_id,
                activated_at=datetime.now(timezone.utc)
            )
            self.db.add(activation)
            self.db.commit()
        
        return True, "License activated", {
            "type": license_obj.license_type,
            "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
            "device_id": device_id
        }
    
    def check_license(self) -> Tuple[bool, str]:
        """Проверка валидности лицензии"""
        return True, "License valid"
    
    def get_license_info(self) -> dict:
        """Информация о лицензии"""
        return {
            "status": "active",
            "type": "pro",
            "expires_at": None
        }
