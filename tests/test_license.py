import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from app.services.license_service import LicenseService
from app.models.face_id import License, LicenseActivation

class TestLicenseService:
    def test_verify_license_not_found(self):
        db = MagicMock()
        service = LicenseService(db)
        db.query.return_value.filter.return_value.first.return_value = None
        valid, msg, info = service.verify_license("INVALID", "dev1")
        assert valid == False
        assert "не найдена" in msg

    def test_verify_license_expired(self):
        db = MagicMock()
        service = LicenseService(db)
        license = MagicMock()
        license.is_revoked = False
        license.is_active = True
        license.expires_at = datetime.utcnow() - timedelta(days=1)
        db.query.return_value.filter.return_value.first.return_value = license
        valid, msg, info = service.verify_license("KEY", "dev1")
        assert valid == False
        assert "истекла" in msg

    def test_check_limits(self):
        db = MagicMock()
        service = LicenseService(db)
        license = MagicMock()
        license.max_users = 100
        license.max_clients = 1000
        license.max_terminals = 5
        db.query.return_value.filter.return_value.first.return_value = license
        db.query.return_value.count.side_effect = [50, 200, 3]
        result = service.check_system_limits("KEY")
        assert result["valid"] == True
        assert result["users"]["available"] == 50
        assert result["clients"]["available"] == 800
