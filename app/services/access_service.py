# app/services/access_service.py

from datetime import datetime, date, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.device import Device
from app.models.subscription import Subscription
from app.models.visit import Visit
from app.models.locker_session import LockerSession
from app.schemas.access import (
    AccessCheckResponse,
    AccessGrantResponse,
    AccessExitResponse,
)
from app.schemas.enums import AccessDecision, AccessMethod
from app.services.visit_service import VisitService
from app.services.subscription_lifecycle_service import SubscriptionLifecycleService
from app.services.locker_service import LockerService
from app.models.locker import Locker


class AccessService:
    """
    Сервис для работы с СКУД/турникетами.
    Работает даже если устройства не настроены — просто пропускает шаги с ними.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.visit_service = VisitService(db)
        self.subscription_service = SubscriptionLifecycleService(db)
        self.locker_service = LockerService(db)
    
    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================
    
    def _get_device(self, device_id: str) -> Device | None:
        """Получить устройство из БД (опционально)"""
        try:
            return self.db.query(Device).filter(Device.code == device_id).first()
        except Exception:
            return None
    
    def _find_client_by_credential(self, credential: str) -> Client | None:
        """Найти клиента по credential (QR-код или UID RFID)"""
        from app.models.credential import Credential
        credential_record = self.db.query(Credential).filter(
            Credential.credential_value == credential,
            Credential.status == "ACTIVE"
        ).first()
        
        if credential_record:
            return self.db.query(Client).filter(Client.id == credential_record.client_id).first()
        
        # Поиск по email или телефону (для QR)
        client = self.db.query(Client).filter(Client.email == credential).first()
        if client:
            return client
        
        client = self.db.query(Client).filter(Client.phone == credential).first()
        return client
    
    def _get_active_subscription(self, client_id: str) -> Subscription | None:
        """Получить активный абонемент клиента"""
        today = date.today()
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.client_id == client_id,
                Subscription.is_active == True,
                Subscription.status == "ACTIVE",
                Subscription.end_date >= today,
            )
            .first()
        )
    
    def _send_open_command(self, device: Device, sector: int = 0) -> bool:
        """
        Отправить команду открытия на устройство KERONG.
        
        Для офлайн замков KERONG поддерживаются сектора:
        - sector=0: шкаф для переодевания
        - sector=1: сейфовая ячейка
        """
        try:
            if device.protocol == "http":
                print(f"[DEVICE] HTTP open command (sector {sector}) sent to {device.address}")
                return True
            elif device.protocol == "mqtt":
                print(f"[DEVICE] MQTT open command (sector {sector}) sent to {device.address}")
                return True
            elif device.protocol == "kerong":
                print(f"[KERONG] Open command (sector {sector}) sent to device {device.code}")
                return True
            else:
                print(f"[WARN] Device {device.code} has unsupported protocol: {device.protocol}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to send open command to {device.code}: {e}")
            return False
    
    # ==========================================================
    # ПРОВЕРКА ДОСТУПА
    # ==========================================================
    
    def check_access(
        self,
        credential: str,
        device_id: str,
        zone: str | None = None,
    ) -> AccessCheckResponse:
        """Проверить, может ли клиент пройти (без создания посещения)"""
        device = self._get_device(device_id)
        client = self._find_client_by_credential(credential)
        
        if not client:
            return AccessCheckResponse(
                decision=AccessDecision.DENY,
                reason="Клиент не найден",
            )
        
        if not client.is_active or client.status != "ACTIVE":
            return AccessCheckResponse(
                decision=AccessDecision.DENY,
                reason="Клиент заблокирован или неактивен",
                client_id=client.id,
                client_name=f"{client.first_name} {client.last_name}",
            )
        
        subscription = self._get_active_subscription(client.id)
        
        if not subscription:
            return AccessCheckResponse(
                decision=AccessDecision.DENY,
                reason="Нет активного абонемента",
                client_id=client.id,
                client_name=f"{client.first_name} {client.last_name}",
            )
        
        if not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                return AccessCheckResponse(
                    decision=AccessDecision.DENY,
                    reason="Лимит посещений исчерпан",
                    client_id=client.id,
                    client_name=f"{client.first_name} {client.last_name}",
                    subscription_status=subscription.status,
                    visits_left=0,
                    subscription_end_date=subscription.end_date,
                )
        
        if subscription.end_date < date.today():
            return AccessCheckResponse(
                decision=AccessDecision.DENY,
                reason="Срок абонемента истёк",
                client_id=client.id,
                client_name=f"{client.first_name} {client.last_name}",
                subscription_status=subscription.status,
                subscription_end_date=subscription.end_date,
            )
        
        visits_left = None
        if not subscription.is_unlimited:
            visits_left = subscription.visit_limit - subscription.visits_used
        
        return AccessCheckResponse(
            decision=AccessDecision.ALLOW,
            reason=None,
            client_id=client.id,
            client_name=f"{client.first_name} {client.last_name}",
            subscription_status=subscription.status,
            visits_left=visits_left,
            subscription_end_date=subscription.end_date,
        )
    
    # ==========================================================
    # ПРЕДОСТАВЛЕНИЕ ДОСТУПА (ВХОД)
    # ==========================================================
    
    def grant_access(
        self,
        credential: str,
        device_id: str,
        zone: str | None = None,
        override: bool = False,
        override_by_user_id: UUID | None = None,
        sector: int = 0,
    ) -> AccessGrantResponse:
        """
        Предоставить доступ (вход).
        
        Args:
            sector: для KERONG замков — сектор (0=шкаф, 1=сейф)
        """
        device = self._get_device(device_id)
        client = self._find_client_by_credential(credential)
        
        if not client:
            return AccessGrantResponse(
                granted=False,
                reason="Клиент не найден",
            )
        
        access_check = self.check_access(credential, device_id, zone)
        
        if access_check.decision == AccessDecision.DENY and not override:
            return AccessGrantResponse(
                granted=False,
                reason=access_check.reason,
                client_id=client.id,
                client_name=f"{client.first_name} {client.last_name}",
            )
        
        access_method = AccessMethod.OVERRIDE if override else AccessMethod.QR
        subscription = self._get_active_subscription(client.id)
        
        # Проверяем, нет ли активного посещения
        active_visit = self.db.query(Visit).filter(
            Visit.client_id == client.id,
            Visit.status == "ACTIVE",
            Visit.exit_time.is_(None),
        ).first()
        
        if active_visit:
            return AccessGrantResponse(
                granted=False,
                reason="Клиент уже в клубе",
                client_id=client.id,
                client_name=f"{client.first_name} {client.last_name}",
            )
        
        # Создаём посещение
        visit = self.visit_service.entry(
            client_id=client.id,
            subscription_id=subscription.id if subscription else None,
            access_method=access_method,
            access_device_id=device_id,
            zone=zone,
        )
        
        # Списываем визит
        if subscription and not subscription.is_unlimited:
            subscription.visits_used += 1
            self.db.commit()
        
        # Отправляем команду на турникет (с учётом сектора)
        open_success = False
        if device and device.protocol != "none":
            open_success = self._send_open_command(device, sector)
        
        if device and not open_success:
            print(f"[WARN] Failed to open turnstile for client {client.id}, but visit recorded")
        
        return AccessGrantResponse(
            granted=True,
            reason=None,
            client_id=client.id,
            client_name=f"{client.first_name} {client.last_name}",
            visit_id=visit.id,
        )
    
    # ==========================================================
    # ВЫХОД
    # ==========================================================
    
    def exit_access(
        self,
        credential: str,
        device_id: str,
    ) -> AccessExitResponse:
        """Обработка выхода. Завершает активное посещение."""
        client = self._find_client_by_credential(credential)
    
        if not client:
            return AccessExitResponse(
                success=False,
                reason="Клиент не найден",
            )
    
        # Проверка: есть ли активный ONLINE шкафчик?
        active_locker_session = self.db.query(LockerSession).filter(
            LockerSession.client_id == client.id,
            LockerSession.status == "ACTIVE",
            LockerSession.lock_type == "ONLINE",
        ).first()
    
        if active_locker_session:
            locker = self.db.query(Locker).filter(Locker.id == active_locker_session.locker_id).first()
            locker_number = locker.number if locker else "неизвестен"
            return AccessExitResponse(
                success=False,
                reason=f"Закройте онлайн шкафчик №{locker_number} перед выходом",
            )
    
        # Ищем активное посещение
        active_visit = self.db.query(Visit).filter(
            Visit.client_id == client.id,
            Visit.status == "ACTIVE",
            Visit.exit_time.is_(None),
        ).first()
    
        if not active_visit:
            return AccessExitResponse(
                success=False,
                reason="Нет активного посещения",
            )
    
        # Закрываем посещение
        completed_visit = self.visit_service.exit(
            visit_id=active_visit.id,
            exit_time=datetime.now(),
        )    
        return AccessExitResponse(
            success=True,
            reason=None,
            visit_id=completed_visit.id,
            duration_minutes=completed_visit.duration_minutes,
        )