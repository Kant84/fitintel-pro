# celery_app.py

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "fitnexus",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    beat_schedule={
        # ==========================================================
        # M03 — VISITS
        # ==========================================================
        "close-incomplete-visits": {
            "task": "visits.close_incomplete",
            "schedule": 3600.0,  # каждый час
        },
        "update-visits-stats": {
            "task": "visits.update_stats",
            "schedule": 86400.0,  # раз в день
        },
        "archive-old-visits": {
            "task": "visits.archive_old",
            "schedule": 604800.0,  # раз в неделю
        },
        "sync-to-external": {
            "task": "visits.sync_external",
            "schedule": 86400.0,  # раз в день
            "kwargs": {
                "start_date": "2026-04-15",
                "end_date": "2026-04-16",
            },
        },
        
        # ==========================================================
        # M04 — ACCESS CONTROL
        # ==========================================================
        "access-cache-cleanup": {
            "task": "access.cache.cleanup",
            "schedule": 3600.0,  # каждый час
        },
        "access-cache-refresh-all": {
            "task": "access.cache.refresh_all",
            "schedule": 86400.0,  # раз в день
        },
        "access-credentials-expire": {
            "task": "access.credentials.expire",
            "schedule": 86400.0,  # раз в день
        },
        "access-sync-external": {
            "task": "access.sync_external",
            "schedule": 3600.0,  # каждый час
            "kwargs": {"system_type": None},
        },
        "access-close-stale-locker-sessions": {
            "task": "access.close_stale_locker_sessions",
            "schedule": 1800.0,  # каждые 30 минут
            "kwargs": {"hours_threshold": 12},
        },
        
        # ==========================================================
        # M05 — FINANCE
        # ==========================================================
        "finance-send-pending-receipts": {
            "task": "finance.receipts.send_pending",
            "schedule": 3600.0,  # каждый час
        },
        "finance-sync-ofd": {
            "task": "finance.receipts.sync_ofd",
            "schedule": 1800.0,  # каждые 30 минут
        },
        "finance-auto-close-cash-desk": {
            "task": "finance.cash_desk.auto_close",
            "schedule": 3600.0,  # каждый час
            "kwargs": {"hours_threshold": 24},
        },
        "finance-cancel-pending-payments": {
            "task": "finance.payments.cancel_pending",
            "schedule": 3600.0,  # каждый час
            "kwargs": {"hours_threshold": 24},
        },
        "finance-sync-payments-external": {
            "task": "finance.payments.sync_external",
            "schedule": 1800.0,  # каждые 30 минут
        },
        "finance-subscription-expiry-notifications": {
            "task": "finance.subscription.expiry_notifications",
            "schedule": 86400.0,  # раз в день
            "kwargs": {"days_before": 3},
        },
        "finance-archive-wallet-transactions": {
            "task": "finance.wallet.archive_transactions",
            "schedule": 604800.0,  # раз в неделю
            "kwargs": {"days_to_keep": 365},
        },
    },
)

# Автоматически находим задачи
celery_app.autodiscover_tasks(["app.tasks"])