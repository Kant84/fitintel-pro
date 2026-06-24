import hashlib
import os
<<<<<<< HEAD
from datetime import datetime, timezone, timedelta
=======
from datetime import datetime, timedelta, timezone
>>>>>>> add08324efb53366e13ed9684e0652c6bdaa9143
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.face_id import License, LicenseActivation

class LicenseService:
    def __init__(self, db: Session):
        self.db = db

    def verify_license(self, license_key: str, device_id: str) -> Tuple[bool, str, dict]:
        license = self.db.query(License).filter(License.license_key == license_key).first()
        if not license:
            return False, "Лицензия не найдена", {}
        if license.is_revoked:
            return False, "Лицензия отозвана", {}
        if not license.is_active:
            return False, "Лицензия неактивна", {}
        if license.expires_at < datetime.now(timezone.utc):
            return False, f"Лицензия истекла {license.expires_at}", {}

        activation = self.db.query(LicenseActivation).filter(
            LicenseActivation.license_id == license.id,
            LicenseActivation.device_id == device_id
        ).first()

        if not activation:
            active_count = self.db.query(LicenseActivation).filter(
                LicenseActivation.license_id == license.id,
                LicenseActivation.is_active == True
            ).count()
            if active_count >= license.max_terminals:
                return False, f"Превышен лимит активаций ({license.max_terminals})", {}
            activation = LicenseActivation(license_id=license.id, device_id=device_id, is_active=True)
            self.db.add(activation)
            self.db.commit()
        else:
            if not activation.is_active:
                return False, "Активация деактивирована", {}
            activation.last_seen_at = datetime.now(timezone.utc)
            self.db.commit()

        return True, "Лицензия валидна", {
            "license_type": license.license_type,
            "expires_at": license.expires_at.isoformat(),
            "max_users": license.max_users,
            "max_clients": license.max_clients,
            "max_terminals": license.max_terminals
        }

    def check_system_limits(self, license_key: str) -> dict:
        license = self.db.query(License).filter(License.license_key == license_key).first()
        if not license:
            return {"valid": False}
        from app.models.user import User
        from app.models.client import Client
        current_users = self.db.query(User).count()
        current_clients = self.db.query(Client).count()
        current_terminals = self.db.query(LicenseActivation).filter(
            LicenseActivation.license_id == license.id,
            LicenseActivation.is_active == True
        ).count()
        return {
            "valid": True,
            "users": {"current": current_users, "limit": license.max_users, "available": max(0, license.max_users - current_users)},
            "clients": {"current": current_clients, "limit": license.max_clients, "available": max(0, license.max_clients - current_clients)},
            "terminals": {"current": current_terminals, "limit": license.max_terminals, "available": max(0, license.max_terminals - current_terminals)}
        }

    def generate_license(self, owner_name: str, owner_email: str,
                         license_type: str = "standard", months: int = 12,
                         max_users: int = 100, max_clients: int = 1000,
                         max_terminals: int = 5) -> str:
        raw = f"{owner_email}:{datetime.now(timezone.utc).isoformat()}:{os.urandom(16).hex()}"
        license_key = hashlib.sha256(raw.encode()).hexdigest()[:32].upper()
        expires = datetime.now(timezone.utc) + timedelta(days=30 * months)
        license = License(
            license_key=license_key, owner_name=owner_name, owner_email=owner_email,
            license_type=license_type, max_users=max_users, max_clients=max_clients,
            max_terminals=max_terminals, expires_at=expires
        )
        self.db.add(license)
        self.db.commit()
        return license_key

    def revoke_license(self, license_key: str) -> bool:
        license = self.db.query(License).filter(License.license_key == license_key).first()
        if not license:
            return False
        license.is_revoked = True
        license.is_active = False
        for act in license.activations:
            act.is_active = False
            act.deactivated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def deactivate_device(self, license_key: str, device_id: str) -> bool:
        activation = self.db.query(LicenseActivation).join(License).filter(
            License.license_key == license_key,
            LicenseActivation.device_id == device_id
        ).first()
        if not activation:
            return False
        activation.is_active = False
        activation.deactivated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True
