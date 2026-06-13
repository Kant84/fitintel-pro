import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from app.services.face_id_service import FaceIDService
from app.models.face_id import FaceTemplate, FaceRecognitionLog, EmployeeShift
from app.models.user import User
from app.models.client import Client
from app.models.subscription import Subscription
from app.models.visit import SingleTraining

class TestFaceIDService:
    def test_find_best_match(self):
        db = MagicMock()
        service = FaceIDService(db)
        template = MagicMock()
        template.face_encoding = [0.1, 0.2, 0.3]
        template.is_active = True
        db.query.return_value.filter.return_value.all.return_value = [template]
        result = service._find_best_match([0.1, 0.2, 0.3])
        assert result == template

    def test_check_employee_no_shift(self):
        db = MagicMock()
        service = FaceIDService(db)
        user = MagicMock()
        user.is_active = True
        user.is_fired = False
        db.query.return_value.filter.return_value.first.return_value = user
        db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = None
        can_enter, reason = service._check_employee_access(1)
        assert can_enter == False
        assert "Нет активной смены" in reason

    def test_check_employee_fired(self):
        db = MagicMock()
        service = FaceIDService(db)
        user = MagicMock()
        user.is_active = True
        user.is_fired = True
        db.query.return_value.filter.return_value.first.return_value = user
        can_enter, reason = service._check_employee_access(1)
        assert can_enter == False
        assert "уволен" in reason

    def test_check_client_no_subscription(self):
        db = MagicMock()
        service = FaceIDService(db)
        client = MagicMock()
        client.id = 1
        db.query.return_value.filter.return_value.first.side_effect = [client, None, None]
        can_enter, reason = service._check_client_access(1)
        assert can_enter == False
        assert "Нет активного абонемента" in reason
