# add_access_service_methods.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорты
old_imports = '''from app.schemas.access import (
    AccessCheckResponse,
    AccessGrantResponse,
    AccessExitResponse,
)'''

new_imports = '''from app.schemas.access import (
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
)'''

if old_imports in content:
    content = content.replace(old_imports, new_imports)
    print("1. Импорты обновлены!")
else:
    print("ERROR 1: Не найдены импорты")

# Добавляем новые методы в конец класса
new_methods = '''
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
                device_id=log.after_data.get("device_id") if log.after_data else None,
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
'''

# Находим конец класса и добавляем методы
content = content.rstrip() + "\n" + new_methods

with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Новые методы добавлены в AccessService!")
