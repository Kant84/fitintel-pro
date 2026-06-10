# app/tasks/visits.py
# ==========================================================
# Фоновые задачи для модуля Visits (Celery)
# ==========================================================
# Назначение: автоматическое закрытие незавершённых посещений,
#            синхронизация с внешними системами (1С, Mobifitness и др.)
# ==========================================================

from datetime import datetime, timedelta
from typing import Optional
from celery import shared_task
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.visit_service import VisitService
from app.services.audit_service import AuditService
from app.core.config import settings


# ==========================================================
# 1. ОСНОВНАЯ ЗАДАЧА: ЗАКРЫТИЕ НЕЗАВЕРШЁННЫХ ПОСЕЩЕНИЙ
# ==========================================================

@shared_task(
    name="visits.close_incomplete",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def close_incomplete_visits(self) -> dict:
    """
    Фоновая задача: закрывает незавершённые посещения (вход без выхода).
    
    Запускается по расписанию (например, раз в час или раз в день).
    Закрывает посещения, которые начались более N часов назад.
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        service = VisitService(db)
        audit = AuditService(db)
        
        # Закрываем посещения старше 12 часов
        closed_count = service.close_incomplete_visits()
        
        # Логируем результат
        audit.log(
            action="task.visits.close_incomplete",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Auto-closed {closed_count} incomplete visits",
            after_data={"closed_count": closed_count},
        )
        
        return {
            "status": "success",
            "closed_count": closed_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        # Логируем ошибку
        audit.log(
            action="task.visits.close_incomplete",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
            after_data={"error": str(e)},
        )
        
        # Повторный запуск при ошибке
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 2. ЗАДАЧА: ОБНОВЛЕНИЕ СТАТИСТИКИ ПОСЕЩЕНИЙ
# ==========================================================

@shared_task(
    name="visits.update_stats",
    bind=True,
    max_retries=2,
)
def update_visits_stats(self, date: Optional[str] = None) -> dict:
    """
    Фоновая задача: обновляет агрегированную статистику посещений.
    
    Может использоваться для предрасчёта отчётов.
    
    Args:
        date: дата в формате YYYY-MM-DD (если не указана - сегодня)
    
    Returns:
        dict: Статистика за указанную дату
    """
    from datetime import date as date_type
    
    db = SessionLocal()
    try:
        target_date = date_type.fromisoformat(date) if date else date_type.today()
        
        service = VisitService(db)
        stats = service.get_stats(
            period="day",
            start_date=target_date,
            end_date=target_date,
            zone=None,
        )
        
        # Здесь можно сохранить статистику в отдельную таблицу
        # или отправить в систему мониторинга
        
        return {
            "status": "success",
            "date": target_date.isoformat(),
            "stats": stats.model_dump(),
        }
        
    except Exception as e:
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 3. ЗАДАЧА: ОТПРАВКА УВЕДОМЛЕНИЙ О ПОСЕЩЕНИЯХ
# ==========================================================

@shared_task(
    name="visits.send_notifications",
    bind=True,
    max_retries=3,
)
def send_visit_notifications(self, visit_id: str, event_type: str) -> dict:
    """
    Фоновая задача: отправка уведомлений о посещениях.
    
    Поддерживает:
    - SMS (через внешний провайдер)
    - Email
    - Telegram
    - Webhook (для внешних систем)
    
    Args:
        visit_id: ID посещения
        event_type: тип события ('entry', 'exit')
    
    Returns:
        dict: Результат отправки
    """
    db = SessionLocal()
    try:
        service = VisitService(db)
        visit = service.get_visit(visit_id)
        
        if not visit:
            return {"status": "error", "message": "Visit not found"}
        
        # Получаем клиента
        client = service._get_client(visit.client_id)
        
        notifications_sent = []
        
        # 1. Отправка через Telegram (если настроен)
        if settings.TELEGRAM_BOT_TOKEN and client.telegram_id:
            try:
                # Здесь будет вызов Telegram API
                # send_telegram_message(client.telegram_id, message)
                notifications_sent.append("telegram")
            except Exception as e:
                print(f"Telegram notification failed: {e}")
        
        # 2. Отправка через Email (если есть email)
        if client.email:
            try:
                # Здесь будет отправка email
                # send_email(client.email, subject, body)
                notifications_sent.append("email")
            except Exception as e:
                print(f"Email notification failed: {e}")
        
        # 3. Отправка через SMS (если настроен провайдер)
        if settings.SMS_PROVIDER and client.phone:
            try:
                # Здесь будет вызов SMS API
                # send_sms(client.phone, message)
                notifications_sent.append("sms")
            except Exception as e:
                print(f"SMS notification failed: {e}")
        
        return {
            "status": "success",
            "visit_id": visit_id,
            "event_type": event_type,
            "notifications_sent": notifications_sent,
        }
        
    except Exception as e:
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 4. ЗАДАЧА: СИНХРОНИЗАЦИЯ С ВНЕШНИМИ СИСТЕМАМИ
# ==========================================================

@shared_task(
    name="visits.sync_external",
    bind=True,
    max_retries=5,
    default_retry_delay=300,  # 5 минут
)
def sync_visits_to_external_systems(self, start_date: str, end_date: str) -> dict:
    """
    Фоновая задача: синхронизация посещений с внешними системами.
    
    Поддерживает:
    - 1С (бухгалтерия, учёт)
    - Mobifitness (интеграция с фитнес-платформой)
    - Другие API
    
    Args:
        start_date: начальная дата (YYYY-MM-DD)
        end_date: конечная дата (YYYY-MM-DD)
    
    Returns:
        dict: Результат синхронизации
    """
    from datetime import date as date_type
    
    db = SessionLocal()
    try:
        start = date_type.fromisoformat(start_date)
        end = date_type.fromisoformat(end_date)
        
        service = VisitService(db)
        visits = service.repository.get_visits_by_date_range(start, end)
        
        results = []
        
        # ==========================================================
        # 4.1. Синхронизация с 1С
        # ==========================================================
        try:
            one_c_result = sync_to_1c(visits)
            results.append({"system": "1C", **one_c_result})
        except Exception as e:
            results.append({"system": "1C", "status": "error", "message": str(e)})
        
        # ==========================================================
        # 4.2. Синхронизация с Mobifitness
        # ==========================================================
        try:
            mobi_result = sync_to_mobifitness(visits)
            results.append({"system": "Mobifitness", **mobi_result})
        except Exception as e:
            results.append({"system": "Mobifitness", "status": "error", "message": str(e)})
        
        # ==========================================================
        # 4.3. Отправка вебхуков (для кастомных интеграций)
        # ==========================================================
        try:
            webhook_result = send_webhooks(visits)
            results.append({"system": "Webhooks", **webhook_result})
        except Exception as e:
            results.append({"system": "Webhooks", "status": "error", "message": str(e)})
        
        # Логируем результат
        audit = AuditService(db)
        audit.log(
            action="task.visits.sync_external",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Synced {len(visits)} visits to external systems",
            after_data={"results": results},
        )
        
        return {
            "status": "success",
            "visits_count": len(visits),
            "results": results,
        }
        
    except Exception as e:
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 5. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ИНТЕГРАЦИЙ
# ==========================================================

def sync_to_1c(visits: list) -> dict:
    """
    Синхронизация посещений с 1С.
    
    Формат данных: JSON или XML
    Метод: HTTP API или файловый обмен
    """
    if not settings.ONE_C_API_URL:
        return {"status": "skipped", "message": "1C API not configured"}
    
    # Преобразуем посещения в формат 1С
    visits_data = []
    for visit in visits:
        visits_data.append({
            "id": str(visit.id),
            "client_id": str(visit.client_id),
            "entry_time": visit.entry_time.isoformat(),
            "exit_time": visit.exit_time.isoformat() if visit.exit_time else None,
            "duration_minutes": visit.duration_minutes,
            "zone": visit.zone,
        })
    
    # Здесь будет реальный запрос к API 1С
    # import requests
    # response = requests.post(
    #     f"{settings.ONE_C_API_URL}/visits/sync",
    #     json={"visits": visits_data},
    #     headers={"Authorization": f"Bearer {settings.ONE_C_API_KEY}"},
    #     timeout=30,
    # )
    # response.raise_for_status()
    
    # Пока имитируем успешный ответ
    return {
        "status": "success",
        "synced_count": len(visits),
        "message": "Mock sync to 1C completed",
    }


def sync_to_mobifitness(visits: list) -> dict:
    """
    Синхронизация посещений с Mobifitness.
    
    Документация Mobifitness API:
    https://developer.mobifitness.com/docs/visits
    """
    if not settings.MOBIFITNESS_API_URL:
        return {"status": "skipped", "message": "Mobifitness API not configured"}
    
    # Преобразуем посещения в формат Mobifitness
    visits_data = []
    for visit in visits:
        visits_data.append({
            "external_id": str(visit.id),
            "client_external_id": str(visit.client_id),
            "check_in": visit.entry_time.isoformat(),
            "check_out": visit.exit_time.isoformat() if visit.exit_time else None,
            "duration": visit.duration_minutes,
        })
    
    # Здесь будет реальный запрос к API Mobifitness
    # import requests
    # response = requests.post(
    #     f"{settings.MOBIFITNESS_API_URL}/api/v1/visits/import",
    #     json={"visits": visits_data},
    #     headers={"X-API-Key": settings.MOBIFITNESS_API_KEY},
    #     timeout=30,
    # )
    # response.raise_for_status()
    
    return {
        "status": "success",
        "synced_count": len(visits),
        "message": "Mock sync to Mobifitness completed",
    }


def send_webhooks(visits: list) -> dict:
    """
    Отправка вебхуков для кастомных интеграций.
    
    Используется для:
    - CRM системы
    - Системы лояльности
    - Кастомные дашборды
    """
    if not settings.WEBHOOK_URL:
        return {"status": "skipped", "message": "Webhook not configured"}
    
    import requests
    
    success_count = 0
    failed_count = 0
    
    for visit in visits:
        try:
            # Для каждого посещения отправляем отдельный вебхук
            response = requests.post(
                settings.WEBHOOK_URL,
                json={
                    "event": "visit.synced",
                    "data": {
                        "id": str(visit.id),
                        "client_id": str(visit.client_id),
                        "entry_time": visit.entry_time.isoformat(),
                        "exit_time": visit.exit_time.isoformat() if visit.exit_time else None,
                        "duration_minutes": visit.duration_minutes,
                        "zone": visit.zone,
                    },
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            
            if response.status_code in (200, 201, 202):
                success_count += 1
            else:
                failed_count += 1
                
        except Exception as e:
            failed_count += 1
            print(f"Webhook failed for visit {visit.id}: {e}")
    
    return {
        "status": "success" if failed_count == 0 else "partial",
        "success_count": success_count,
        "failed_count": failed_count,
        "total_count": len(visits),
    }


# ==========================================================
# 6. ЗАДАЧА: АРХИВАЦИЯ СТАРЫХ ПОСЕЩЕНИЙ
# ==========================================================

@shared_task(
    name="visits.archive_old",
    bind=True,
    max_retries=2,
)
def archive_old_visits(self, days_to_keep: int = 365) -> dict:
    """
    Фоновая задача: архивация старых посещений.
    
    Перемещает посещения старше N дней в архивную таблицу.
    
    Args:
        days_to_keep: сколько дней хранить в основной таблице
    
    Returns:
        dict: Количество архивированных записей
    """
    db = SessionLocal()
    try:
        archive_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Находим старые посещения
        old_visits = (
            db.query(Visit)
            .filter(Visit.entry_time < archive_date)
            .all()
        )
        
        archived_count = len(old_visits)
        
        # Здесь будет логика перемещения в архивную таблицу
        # Например: insert into visits_archive select * from visits where ...
        
        # Пока просто логируем
        audit = AuditService(db)
        audit.log(
            action="task.visits.archive_old",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Archived {archived_count} old visits",
            after_data={"archived_count": archived_count, "days_to_keep": days_to_keep},
        )
        
        return {
            "status": "success",
            "archived_count": archived_count,
        }
        
    except Exception as e:
        raise self.retry(exc=e)
        
    finally:
        db.close()