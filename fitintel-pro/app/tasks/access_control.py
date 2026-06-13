# app/tasks/access_control.py
# ==========================================================
# Фоновые задачи для модуля Access Control
# ==========================================================
# Назначение:
# - Очистка просроченного кэша доступа
# - Инвалидация кэша при изменении прав
# - Синхронизация с внешними системами (1С, СКУД)
# - Обработка офлайн-журналов с терминалов
# - Обновление статусов учётных данных
# ==========================================================

from datetime import datetime, timedelta, date
from typing import Optional
from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.access_cache_service import AccessCacheService
from app.services.credential_service import CredentialService
from app.services.locker_service import LockerService
from app.services.audit_service import AuditService
from app.repositories.external_sync_repository import ExternalSyncRepository
from app.core.config import settings


# ==========================================================
# 1. ОЧИСТКА ПРОСРОЧЕННОГО КЭША
# ==========================================================

@shared_task(
    name="access.cache.cleanup",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def cleanup_expired_cache(self) -> dict:
    """
    Фоновая задача: удаление просроченного кэша доступа.
    
    Запускается по расписанию (каждый час).
    Удаляет кэш, срок действия которого истёк.
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        service = AccessCacheService(db)
        audit = AuditService(db)
        
        # Удаляем просроченный кэш
        deleted_count = service.cleanup_expired_cache()
        
        # Логируем результат
        audit.log(
            action="task.access.cache.cleanup",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Cleaned up {deleted_count} expired cache items",
            after_data={"deleted_count": deleted_count},
        )
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.access.cache.cleanup",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
            after_data={"error": str(e)},
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 2. ОБНОВЛЕНИЕ КЭША ДЛЯ ВСЕХ УСТРОЙСТВ
# ==========================================================

@shared_task(
    name="access.cache.refresh_all",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 минут
)
def refresh_all_caches(self) -> dict:
    """
    Фоновая задача: полное обновление кэша для всех устройств.
    
    Запускается по расписанию (раз в день).
    Перестраивает кэш для всех терминалов и турникетов.
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        service = AccessCacheService(db)
        audit = AuditService(db)
        
        # Обновляем кэш
        items_count = service.refresh_all_caches()
        
        audit.log(
            action="task.access.cache.refresh_all",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Refreshed all caches, {items_count} items created",
            after_data={"items_count": items_count},
        )
        
        return {
            "status": "success",
            "items_count": items_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.access.cache.refresh_all",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
            after_data={"error": str(e)},
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 3. ОЧИСТКА ПРОСРОЧЕННЫХ УЧЁТНЫХ ДАННЫХ
# ==========================================================

@shared_task(
    name="access.credentials.expire",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def expire_old_credentials(self) -> dict:
    """
    Фоновая задача: пометить просроченные учётные данные как EXPIRED.
    
    Запускается по расписанию (раз в день).
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        service = CredentialService(db)
        audit = AuditService(db)
        
        # Помечаем просроченные
        expired_count = service.expire_old_credentials()
        
        audit.log(
            action="task.access.credentials.expire",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Expired {expired_count} credentials",
            after_data={"expired_count": expired_count},
        )
        
        return {
            "status": "success",
            "expired_count": expired_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.access.credentials.expire",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
            after_data={"error": str(e)},
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 4. СИНХРОНИЗАЦИЯ С ВНЕШНИМИ СИСТЕМАМИ (1С, СКУД)
# ==========================================================

@shared_task(
    name="access.sync_external",
    bind=True,
    max_retries=5,
    default_retry_delay=300,  # 5 минут
)
def sync_with_external_systems(self, system_type: str | None = None) -> dict:
    """
    Фоновая задача: синхронизация с внешними системами.
    
    Поддерживает:
    - 1С (бухгалтерия, учёт)
    - СКУД (система контроля доступа)
    - Файловые серверы
    
    Args:
        system_type: тип системы (ONEC, SKUD, FILE_SERVER)
    
    Returns:
        dict: Результат синхронизации
    """
    db = SessionLocal()
    try:
        sync_repo = ExternalSyncRepository(db)
        audit = AuditService(db)
        
        # Получаем ожидающие синхронизации записи
        pending = sync_repo.get_pending(system_type=system_type, limit=100)
        
        results = []
        success_count = 0
        failed_count = 0
        
        for log_entry in pending:
            try:
                # Здесь будет реальная отправка в 1С или СКУД
                # sync_result = send_to_external_system(log_entry)
                
                # Пока эмуляция
                sync_result = {"status": "success"}
                
                if sync_result.get("status") == "success":
                    sync_repo.update_status(
                        log_id=str(log_entry.id),
                        status="SUCCESS",
                        response_data=sync_result,
                    )
                    success_count += 1
                else:
                    sync_repo.update_status(
                        log_id=str(log_entry.id),
                        status="FAILED",
                        error_message=sync_result.get("error", "Unknown error"),
                    )
                    failed_count += 1
                    
            except Exception as e:
                sync_repo.update_status(
                    log_id=str(log_entry.id),
                    status="FAILED",
                    error_message=str(e),
                )
                failed_count += 1
        
        audit.log(
            action="task.access.sync_external",
            status="success" if failed_count == 0 else "partial",
            actor_user_id=None,
            entity_type="system",
            message=f"Synced {success_count} items, failed {failed_count}",
            after_data={
                "system_type": system_type,
                "success_count": success_count,
                "failed_count": failed_count,
            },
        )
        
        return {
            "status": "success" if failed_count == 0 else "partial",
            "system_type": system_type,
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(pending),
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.access.sync_external",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
            after_data={"error": str(e)},
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 5. ОБРАБОТКА ОФЛАЙН-ЖУРНАЛОВ С ТЕРМИНАЛОВ
# ==========================================================

@shared_task(
    name="access.process_offline_logs",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_offline_logs(self, device_id: str, logs: list) -> dict:
    """
    Фоновая задача: обработка офлайн-журналов с терминалов.
    
    Args:
        device_id: ID устройства
        logs: список записей с терминала
    
    Returns:
        dict: Результат обработки
    """
    db = SessionLocal()
    try:
        from app.models.access_log import AccessLog
        from app.services.access_log_repository import AccessLogRepository
        
        log_repo = AccessLogRepository(db)
        audit = AuditService(db)
        
        # Преобразуем логи в модели
        access_logs = []
        for log_data in logs:
            access_log = AccessLog(
                device_id=device_id,
                credential_value=log_data.get("credential_value"),
                credential_type=log_data.get("credential_type"),
                client_id=log_data.get("client_id"),
                decision=log_data.get("decision", "ERROR"),
                reason=log_data.get("reason"),
                mode="offline",
                cache_used=log_data.get("cache_used", True),
                request_data=log_data.get("request_data"),
                response_data=log_data.get("response_data"),
                created_at=datetime.fromisoformat(log_data.get("timestamp")),
            )
            access_logs.append(access_log)
        
        # Сохраняем в БД
        saved_count = log_repo.add_bulk(access_logs)
        
        audit.log(
            action="task.access.process_offline_logs",
            status="success",
            actor_user_id=None,
            entity_type="device",
            entity_id=device_id,
            message=f"Processed {saved_count} offline logs from device {device_id}",
            after_data={"device_id": device_id, "logs_count": saved_count},
        )
        
        return {
            "status": "success",
            "device_id": device_id,
            "processed_count": saved_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.access.process_offline_logs",
            status="error",
            actor_user_id=None,
            entity_type="device",
            entity_id=device_id,
            message=f"Error: {str(e)}",
            after_data={"error": str(e)},
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 6. АВТОМАТИЧЕСКОЕ ЗАКРЫТИЕ ЗАВИСШИХ СЕССИЙ ШКАФЧИКОВ
# ==========================================================

@shared_task(
    name="access.close_stale_locker_sessions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def close_stale_locker_sessions(self, hours_threshold: int = 12) -> dict:
    """
    Фоновая задача: закрытие зависших сессий шкафчиков.
    
    Закрывает сессии, которые активны более N часов.
    
    Args:
        hours_threshold: порог в часах
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.repositories.locker_session_repository import LockerSessionRepository
        from app.repositories.locker_repository import LockerRepository
        
        session_repo = LockerSessionRepository(db)
        locker_repo = LockerRepository(db)
        audit = AuditService(db)
        
        # Получаем все активные сессии
        active_sessions = session_repo.list_active_sessions()
        
        threshold = datetime.now() - timedelta(hours=hours_threshold)
        stale_sessions = [s for s in active_sessions if s.started_at < threshold]
        
        closed_count = 0
        for session in stale_sessions:
            # Закрываем сессию
            session.status = "CLOSED"
            session.ended_at = datetime.now()
            session.notes = f"Автоматически закрыта (активна > {hours_threshold}ч)"
            
            # Освобождаем шкафчик
            locker = locker_repo.get_by_id(session.locker_id)
            if locker:
                locker.status = "FREE"
            
            closed_count += 1
        
        if closed_count > 0:
            db.commit()
        
        audit.log(
            action="task.access.close_stale_locker_sessions",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Closed {closed_count} stale locker sessions",
            after_data={"closed_count": closed_count, "hours_threshold": hours_threshold},
        )
        
        return {
            "status": "success",
            "closed_count": closed_count,
            "hours_threshold": hours_threshold,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.access.close_stale_locker_sessions",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
            after_data={"error": str(e)},
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 7. ОТПРАВКА УВЕДОМЛЕНИЙ О НЕУДАЧНЫХ ПОПЫТКАХ ДОСТУПА
# ==========================================================

@shared_task(
    name="access.send_access_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_access_alert(self, credential_value: str, reason: str, attempts: int) -> dict:
    """
    Фоновая задача: отправка уведомлений о неудачных попытках доступа.
    
    Args:
        credential_value: учётные данные
        reason: причина отказа
        attempts: количество попыток
    
    Returns:
        dict: Результат отправки
    """
    db = SessionLocal()
    try:
        from app.repositories.credential_repository import CredentialRepository
        from app.models.client import Client
        
        credential_repo = CredentialRepository(db)
        audit = AuditService(db)
        
        credential = credential_repo.get_by_value(credential_value)
        
        if not credential:
            return {"status": "skipped", "reason": "Credential not found"}
        
        client = db.query(Client).filter(Client.id == credential.client_id).first()
        
        if not client:
            return {"status": "skipped", "reason": "Client not found"}
        
        notifications_sent = []
        
        # Отправка email (если настроен)
        if client.email and settings.SMTP_HOST:
            # send_email(client.email, subject, body)
            notifications_sent.append("email")
        
        # Отправка SMS (если настроен)
        if client.phone and settings.SMS_PROVIDER:
            # send_sms(client.phone, message)
            notifications_sent.append("sms")
        
        # Логируем
        audit.log(
            action="access.alert.sent",
            status="success",
            actor_user_id=None,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Access denied alert for client {client.email}: {reason}",
            after_data={
                "credential_value": credential_value,
                "reason": reason,
                "attempts": attempts,
                "notifications": notifications_sent,
            },
        )
        
        return {
            "status": "success",
            "client_id": str(client.id),
            "reason": reason,
            "notifications_sent": notifications_sent,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="access.alert.send",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error sending alert: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()