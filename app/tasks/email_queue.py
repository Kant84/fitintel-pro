# app/tasks/email_queue.py - автообработка email-очереди (A4)
import logging
from celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.process_email_queue")
def process_email_queue():
    """Очередь писем: ретраи 1 -> 5 -> 15 мин, FAILED после 3 попыток."""
    try:
        from app.db.session import SessionLocal
        from app.services.email_queue_service import EmailQueueService

        db = SessionLocal()
        try:
            result = EmailQueueService(db).process_queue()
        finally:
            db.close()
        log.info("[A4] process_email_queue: %s", result)
        return result
    except Exception as e:
        log.error("[A4] process_email_queue failed: %s", e)
        return {"status": "error", "error": str(e)}
