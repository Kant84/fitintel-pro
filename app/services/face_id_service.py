import math
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.face_id import FaceTemplate, FaceRecognitionLog, EmployeeShift
from app.models.user import User
from app.models.client import Client
from app.models.subscription import Subscription
from app.models.visit import SingleTraining

class FaceIDService:
    def __init__(self, db: Session):
        self.db = db

    def recognize_and_grant_access(
        self, face_encoding: list, terminal_id: str, terminal_location: str = None
    ) -> Tuple[bool, str, dict]:
        template = self._find_best_match(face_encoding)
        if not template:
            self._log_access(None, None, None, terminal_id, terminal_location,
                             "denied", "Лицо не распознано", 0.0)
            return False, "Лицо не распознано", {}

        user = template.user
        user_info = {"user_id": user.id, "name": user.full_name, "type": template.user_type}

        if template.user_type in ("employee", "admin", "trainer", "cashier", "manager"):
            can_enter, reason = self._check_employee_access(user.id)
            self._log_access(template.id, user.id, template.user_type, terminal_id,
                             terminal_location, "granted" if can_enter else "denied",
                             reason, 0.95, has_valid_shift=can_enter,
                             is_employee_active=user.is_active, is_fired=getattr(user, 'is_fired', False))
            return can_enter, reason, user_info

        if template.user_type == "client":
            can_enter, reason = self._check_client_access(user.id)
            self._log_access(template.id, user.id, "client", terminal_id,
                             terminal_location, "granted" if can_enter else "denied",
                             reason, 0.95, has_valid_subscription=can_enter)
            return can_enter, reason, user_info

        return False, "Неизвестный тип пользователя", {}

    def _find_best_match(self, face_encoding: list) -> Optional[FaceTemplate]:
        templates = self.db.query(FaceTemplate).filter(FaceTemplate.is_active == True).all()
        best_match = None
        best_score = float('inf')
        for template in templates:
            if not template.face_encoding:
                continue
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(template.face_encoding, face_encoding)))
            if dist < 0.6 and dist < best_score:
                best_score = dist
                best_match = template
        return best_match

    def _check_employee_access(self, employee_id: int) -> Tuple[bool, str]:
        user = self.db.query(User).filter(User.id == employee_id).first()
        if not user or not user.is_active:
            return False, "Сотрудник заблокирован"
        if getattr(user, 'is_fired', False):
            return False, "Сотрудник уволен"
        now = datetime.utcnow()
        active_shift = self.db.query(EmployeeShift).filter(
            EmployeeShift.employee_id == employee_id,
            EmployeeShift.status == "active",
            EmployeeShift.shift_start <= now,
            EmployeeShift.shift_end >= now
        ).first()
        if not active_shift:
            return False, "Нет активной смены"
        return True, "Доступ разрешён"

    def _check_client_access(self, client_user_id: int) -> Tuple[bool, str]:
        client = self.db.query(Client).filter(Client.user_id == client_user_id).first()
        if not client:
            return False, "Клиент не найден"
        now = datetime.utcnow()
        active_sub = self.db.query(Subscription).filter(
            Subscription.client_id == client.id,
            Subscription.status == "active",
            Subscription.start_date <= now,
            Subscription.end_date >= now
        ).first()
        if active_sub:
            return True, f"Абонемент активен до {active_sub.end_date}"
        active_training = self.db.query(SingleTraining).filter(
            SingleTraining.client_id == client.id,
            SingleTraining.is_paid == True,
            SingleTraining.is_used == False,
            SingleTraining.valid_until >= now
        ).first()
        if active_training:
            active_training.is_used = True
            active_training.used_at = now
            self.db.commit()
            return True, "Разовая тренировка активирована"
        return False, "Нет активного абонемента или оплаченной тренировки"

    def _log_access(self, template_id, user_id, user_type, terminal_id, location,
                    status, reason, confidence, has_valid_subscription=None,
                    has_valid_shift=None, is_employee_active=None, is_fired=None):
        log = FaceRecognitionLog(
            face_template_id=template_id, user_id=user_id, user_type=user_type,
            terminal_id=terminal_id, terminal_location=location, status=status,
            reason=reason, confidence_score=confidence,
            has_valid_subscription=has_valid_subscription,
            has_valid_shift=has_valid_shift,
            is_employee_active=is_employee_active,
            is_fired=is_fired
        )
        self.db.add(log)
        self.db.commit()

    def register_face(self, user_id: int, user_type: str, face_encoding: list,
                      photo_path: str = None, quality_score: float = None) -> FaceTemplate:
        # Деактивируем старые primary если новый primary
        existing = self.db.query(FaceTemplate).filter(
            FaceTemplate.user_id == user_id, FaceTemplate.is_active == True
        ).all()
        is_primary = len(existing) == 0
        template = FaceTemplate(
            user_id=user_id, user_type=user_type, face_encoding=face_encoding,
            photo_path=photo_path, quality_score=quality_score,
            is_active=True, is_primary=is_primary
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template
