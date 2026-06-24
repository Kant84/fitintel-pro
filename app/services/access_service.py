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
    AccessOpenResponse,
    AccessManualOpenResponse,
    AccessStatusResponse,
    AccessBlockResponse,
    AccessLogResponse,
    AccessEmergencyUnlockResponse,
    DeviceStatus,
    AccessLogEntry,
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
        Отправить команду открытия на устройство.
        
        Поддерживает:
        - Hardware Manager (реальные драйверы: HTTP, MQTT, KERONG, Modbus, Era, X1)
        - Fallback HTTP прямой запрос
        """
        try:
            # 1. Пробуем через Hardware Manager (реальные драйверы)
            from app.hardware.manager import DeviceManager
            from app.hardware.base import AccessResult
            
            hw_device = DeviceManager.get_device(device.code)
            if hw_device:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(DeviceManager.open_device(device.code, sector=sector))
                if result == AccessResult.GRANTED:
                    print(f"[DEVICE] Hardware Manager open SUCCESS for {device.code} (sector {sector})")
                    return True
                else:
                    print(f"[DEVICE] Hardware Manager open FAILED for {device.code} (sector {sector}), result={result}")
                    return False
            
            # 2. Fallback: прямой HTTP запрос (если нет в Hardware Manager)
            if device.protocol == "http":
                import requests
                import json
                # Формируем payload для HTTP API устройства
                payload = {
                    "action": "open",
                    "device_id": device.code,
                    "sector": sector,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                # Добавляем auth token из config если есть
                headers = {"Content-Type": "application/json"}
                if device.config and isinstance(device.config, dict):
                    if device.config.get("auth_token"):
                        headers["Authorization"] = f"Bearer {device.config['auth_token']}"
                    # Добавляем дополнительные параметры из config
                    extra_params = device.config.get("open_params", {})
                    payload.update(extra_params)
                
                url = device.address or f"http://localhost:8080/api/device/{device.code}/open"
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    print(f"[DEVICE] HTTP open command SUCCESS (sector {sector}) sent to {device.address}, response: {response.status_code}")
                    return True
                else:
                    print(f"[DEVICE] HTTP open command FAILED (sector {sector}) sent to {device.address}, response: {response.status_code}, body: {response.text[:200]}")
                    return False
                    
            elif device.protocol == "mqtt":
                try:
                    import paho.mqtt.client as mqtt
                    import json
                    
                    # Получаем настройки MQTT из config
                    mqtt_config = device.config or {}
                    broker = mqtt_config.get("broker", device.address or "localhost")
                    port = mqtt_config.get("port", 1883)
                    topic = mqtt_config.get("topic", f"devices/{device.code}/command")
                    username = mqtt_config.get("username")
                    password = mqtt_config.get("password")
                    client_id = mqtt_config.get("client_id", f"fitintel_{device.code}")
                    
                    # Создаём клиент
                    client = mqtt.Client(client_id=client_id)
                    if username and password:
                        client.username_pw_set(username, password)
                    
                    # Подключаемся и публикуем
                    client.connect(broker, port, timeout=5)
                    
                    payload = json.dumps({
                        "action": "open",
                        "device_id": device.code,
                        "sector": sector,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    
                    result = client.publish(topic, payload, qos=1)
                    client.disconnect()
                    
                    if result.rc == 0:
                        print(f"[DEVICE] MQTT open command SUCCESS (sector {sector}) sent to {broker}:{port}/{topic}")
                        return True
                    else:
                        print(f"[DEVICE] MQTT open command FAILED (sector {sector}), rc={result.rc}")
                        return False
                        
                except Exception as e:
                    print(f"[ERROR] MQTT failed for {device.code}: {e}")
                    return False
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
    
    def _check_locker_on_exit(self, client_id: str) -> dict:
        """
        Проверить, можно ли клиенту выйти с занятым шкафчиком.
        
        VIP клиенты могут выходить с занятым шкафчиком.
        Остальные должны освободить шкафчик перед выходом.
        
        Returns:
            {"can_exit": True} — можно выходить
            {"can_exit": False, "reason": "..."} — нельзя выходить
        """
        from app.models.locker import Locker
        from app.models.locker_session import LockerSession
        
        # Ищем активную сессию шкафчика клиента
        session = (
            self.db.query(LockerSession)
            .filter(LockerSession.client_id == client_id, LockerSession.status == "ACTIVE")
            .first()
        )
        
        if not session:
            # Нет занятого шкафчика — можно выходить
            return {"can_exit": True}
        
        # Проверяем шкафчик
        locker = self.db.query(Locker).filter(Locker.id == session.locker_id).first()
        if not locker:
            return {"can_exit": True}
        
        # VIP клиенты могут выходить с занятым шкафчиком
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if client and client.client_category == "VIP":
            return {"can_exit": True}
        
        # Обычный шкафчик занят — нельзя выходить!
        return {
            "can_exit": False,
            "reason": f"Шкафчик {locker.number} занят. Освободите шкафчик перед выходом.",
        }
    
    def _get_active_visit(self, client_id: str):
        """Получить активное посещение клиента"""
        from app.models.visit import Visit
        return (
            self.db.query(Visit)
            .filter(Visit.client_id == client_id, Visit.status == "ACTIVE")
            .first()
        )
    
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
                decision=AccessDecision.DENIED,
                reason="Клиент не найден",
            )
        
        # Проверяем, не пытается ли клиент выйти с занятым шкафчиком
        # (кроме VIP и индивидуальных шкафчиков с оплаченной арендой)
        # Проверяем только на выходе (клиент уже внутри)
        if device and device.device_type == "turnstile":
            # Проверяем активное посещение
            active_visit = self._get_active_visit(client.id)
            if active_visit:
                # Клиент внутри — значит это выход
                # Проверяем шкафчик
                locker_check = self._check_locker_on_exit(client.id)
                if not locker_check["can_exit"]:
                    return AccessCheckResponse(
                        decision=AccessDecision.DENIED,
                        reason=locker_check["reason"],
                    )
        
        if not client.is_active or client.status != "ACTIVE":
            return AccessCheckResponse(
                decision=AccessDecision.DENIED,
                reason="Клиент заблокирован или неактивен",
                client_id=client.id,
                client_name=f"{client.first_name} {client.last_name}",
            )
        
        subscription = self._get_active_subscription(client.id)
        
        if not subscription:
            return AccessCheckResponse(
                decision=AccessDecision.DENIED,
                reason="Нет активного абонемента",
                client_id=client.id,
                client_name=f"{client.first_name} {client.last_name}",
            )
        
        if not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                return AccessCheckResponse(
                    decision=AccessDecision.DENIED,
                    reason="Лимит посещений исчерпан",
                    client_id=client.id,
                    client_name=f"{client.first_name} {client.last_name}",
                    subscription_status=subscription.status,
                    visits_left=0,
                    subscription_end_date=subscription.end_date,
                )
        
        if subscription.end_date < date.today():
            return AccessCheckResponse(
                decision=AccessDecision.DENIED,
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
            decision=AccessDecision.ALLOWED,
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
        
        if access_check.decision == AccessDecision.DENIED and not override:
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

    # ==========================================================
    # E9.1-3: ОТКРЫТИЕ ПО КАРТЕ / QR
    # ==========================================================
    
    def open_access(
        self,
        credential: str,
        device_id: str,
        zone: str | None = None,
    ) -> AccessOpenResponse:
        """
        Открыть турникет по карте/QR (E9.1-3).
        
        Проверяет:
        - Устройство не заблокировано
        - Anti-passback (если включён)
        - График доступа (если задан)
        - Абонемент клиента
        """
        # Проверяем устройство
        device = self._get_device(device_id)
        if device and device.is_blocked:
            return AccessOpenResponse(
                granted=False,
                reason="Устройство заблокировано",
                device_id=device_id,
            )
        
        # Проверяем график доступа устройства
        if device and device.work_schedule:
            from datetime import datetime
            now = datetime.now().time()
            schedule = device.work_schedule
            start = schedule.get("start")
            end = schedule.get("end")
            if start and end:
                from datetime import time as dt_time
                start_time = dt_time.fromisoformat(start) if isinstance(start, str) else start
                end_time = dt_time.fromisoformat(end) if isinstance(end, str) else end
                if now < start_time or now > end_time:
                    return AccessOpenResponse(
                        granted=False,
                        reason=f"Доступ запрещён вне рабочего времени ({start}-{end})",
                        device_id=device_id,
                    )
        
        # Проверяем клиента
        client = self._find_client_by_credential(credential)
        if not client:
            return AccessOpenResponse(
                granted=False,
                reason="Карта не найдена",
                device_id=device_id,
            )
        
        # Проверяем anti-passback
        if device and device.anti_passback_enabled:
            active_visit = self.db.query(Visit).filter(
                Visit.client_id == client.id,
                Visit.status == "ACTIVE",
                Visit.exit_time.is_(None),
            ).first()
            if active_visit:
                return AccessOpenResponse(
                    granted=False,
                    reason="Anti-passback: требуется выход",
                    client_id=client.id,
                    client_name=f"{client.first_name} {client.last_name}",
                    device_id=device_id,
                )
        
        # Используем grant_access для создания посещения
        grant_result = self.grant_access(
            credential=credential,
            device_id=device_id,
            zone=zone,
        )
        
        return AccessOpenResponse(
            granted=grant_result.granted,
            reason=grant_result.reason,
            client_id=grant_result.client_id,
            client_name=grant_result.client_name,
            visit_id=grant_result.visit_id,
            turnstile_open=grant_result.granted,
            device_id=device_id,
            zone=zone,
        )
    
    # ==========================================================
    # E9.4-5: РУЧНОЕ ОТКРЫТИЕ (ADMIN)
    # ==========================================================
    
    def manual_open(
        self,
        device_id: str,
        reason: str,
        opened_by_user_id: UUID,
    ) -> AccessManualOpenResponse:
        """
        Ручное открытие турникета (E9.4-5).
        
        - Не проверяет абонемент
        - Записывает в audit
        - Открывает устройство
        """
        device = self._get_device(device_id)
        
        # Отправляем команду открытия
        open_success = False
        if device:
            open_success = self._send_open_command(device)
        else:
            # Устройство не найдено, но открываем "виртуально"
            open_success = True
        
        # Записываем в audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit_log = audit.log(
            action="access.manual_open",
            status="success",
            actor_user_id=opened_by_user_id,
            entity_type="device",
            entity_id=device.id if device else None,
            message=f"Ручное открытие: {reason}",
            after_data={
                "device_id": device_id,
                "reason": reason,
                "opened_by": str(opened_by_user_id),
            },
        )
        
        return AccessManualOpenResponse(
            success=True,
            device_id=device_id,
            opened_by=opened_by_user_id,
            audit_log_id=audit_log.id if audit_log else None,
        )
    
    # ==========================================================
    # E9.6: СТАТУС УСТРОЙСТВ
    # ==========================================================
    
    def get_status(self) -> AccessStatusResponse:
        """Получить статус всех устройств доступа (E9.6)"""
        devices = self.db.query(Device).all()
        
        device_statuses = []
        online_count = 0
        offline_count = 0
        blocked_count = 0
        
        for device in devices:
            # Проверяем онлайн по last_heartbeat (5 минут таймаут)
            is_online = False
            if device.last_heartbeat_at:
                from datetime import datetime, timedelta
                is_online = (datetime.now(timezone.utc) - device.last_heartbeat_at) < timedelta(minutes=5)
            
            if is_online:
                online_count += 1
            else:
                offline_count += 1
            
            if device.is_blocked:
                blocked_count += 1
            
            device_statuses.append(DeviceStatus(
                device_id=device.code,
                name=device.name,
                device_type=device.device_type,
                zone=device.zone,
                online=is_online,
                blocked=device.is_blocked,
                anti_passback=device.anti_passback_enabled,
                last_heartbeat=device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None,
            ))
        
        return AccessStatusResponse(
            devices=device_statuses,
            total=len(devices),
            online=online_count,
            offline=offline_count,
            blocked=blocked_count,
        )
    
    # ==========================================================
    # E9.7-8: БЛОКИРОВКА / РАЗБЛОКИРОВКА
    # ==========================================================
    
    def block_device(
        self,
        device_id: str,
        reason: str,
        blocked_by_user_id: UUID,
    ) -> AccessBlockResponse:
        """Заблокировать устройство (E9.7)"""
        device = self._get_device(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Устройство не найдено",
            )
        
        device.is_blocked = True
        self.db.commit()
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="access.device.blocked",
            status="success",
            actor_user_id=blocked_by_user_id,
            entity_type="device",
            entity_id=device.id,
            message=f"Устройство заблокировано: {reason}",
        )
        
        return AccessBlockResponse(
            success=True,
            device_id=device_id,
            blocked=True,
            reason=reason,
            blocked_by=blocked_by_user_id,
        )
    
    def unblock_device(
        self,
        device_id: str,
    ) -> AccessBlockResponse:
        """Разблокировать устройство (E9.8)"""
        device = self._get_device(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Устройство не найдено",
            )
        
        device.is_blocked = False
        self.db.commit()
        
        return AccessBlockResponse(
            success=True,
            device_id=device_id,
            blocked=False,
        )
    
    # ==========================================================
    # E9.9: ЛОГИ ДОСТУПА
    # ==========================================================
    
    def get_logs(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        device_id: str | None = None,
    ) -> AccessLogResponse:
        """Получить логи доступа (E9.9)"""
        # Используем audit как источник логов
        from app.models.audit import AuditLog
        query = self.db.query(AuditLog).filter(
            AuditLog.action.in_([
                "access.manual_open",
                "access.device.blocked",
                "access.emergency_unlock",
                "visits.entry",
                "visits.exit",
            ])
        )
        
        if date_from:
            from datetime import datetime
            query = query.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            from datetime import datetime
            query = query.filter(AuditLog.created_at <= datetime.fromisoformat(date_to))
        
        logs = query.order_by(AuditLog.created_at.desc()).limit(1000).all()
        
        log_entries = []
        for log in logs:
            log_entries.append(AccessLogEntry(
                id=log.id,
                timestamp=log.created_at.isoformat() if log.created_at else None,
                event_type=log.action.upper().replace(".", "_"),
                client_id=log.entity_id if log.entity_type == "client" else None,
                client_name=log.message,
                device_id=log.after_data.get("device_id") if log.after_data and log.after_data.get("device_id") else "unknown",
                zone=log.after_data.get("zone") if log.after_data else None,
                granted=log.status == "success",
                reason=log.message,
            ))
        
        return AccessLogResponse(
            logs=log_entries,
            total=len(log_entries),
            date_from=date_from,
            date_to=date_to,
        )
    
    # ==========================================================
    # E9.13-14: ЭКСТРЕННОЕ ОТКРЫТИЕ
    # ==========================================================
    
    def emergency_unlock(
        self,
        unlocked_by_user_id: UUID,
    ) -> AccessEmergencyUnlockResponse:
        """Экстренное открытие всех устройств (E9.13-14)"""
        devices = self.db.query(Device).filter(Device.is_active == True).all()
        
        unlocked_devices = []
        for device in devices:
            if not device.is_blocked:
                self._send_open_command(device)
                unlocked_devices.append(device.code)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit_log = audit.log(
            action="access.emergency_unlock",
            status="success",
            actor_user_id=unlocked_by_user_id,
            entity_type="system",
            message=f"Экстренное открытие {len(unlocked_devices)} устройств",
            after_data={
                "unlocked_devices": unlocked_devices,
                "unlocked_by": str(unlocked_by_user_id),
            },
        )
        
        return AccessEmergencyUnlockResponse(
            success=True,
            unlocked_count=len(unlocked_devices),
            unlocked_devices=unlocked_devices,
            unlocked_by=unlocked_by_user_id,
            audit_log_id=audit_log.id if audit_log else None,
            message=f"Открыто {len(unlocked_devices)} устройств",
        )
