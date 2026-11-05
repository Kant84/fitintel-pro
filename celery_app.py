# celery_app.py — Celery application для FitIntel Pro
import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "fitintel",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],  # авто-подключение задач из app/tasks/
)

celery_app.conf.update(
    task_serialization="json",
    accept_content=["json"],
    result_serialization="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    worker_max_tasks_per_child=100,
    task_time_limit=300,
    task_soft_time_limit=240,
    broker_connection_retry_on_startup=True,
)

# Расписание (beat)
celery_app.conf.beat_schedule = {
    "email-queue-process": {
        "task": "app.tasks.process_email_queue",
        "schedule": 60.0,  # A4: каждую минуту
    },
    "locker-rental-reminders": {
        "task": "app.tasks.locker_rental_reminders",
        "schedule": 3600.0,  # каждый час: аренды с истечением <= 72 ч
    },
    "ml-dataset-dump": {
        "task": "app.tasks.dump_parquet",
        "schedule": crontab(hour=4, minute=0),  # E60: ночной дамп в Parquet
    },
        "support-mail-poll": {
        "task": "app.tasks.poll_support_mail",
        "schedule": 300.0,  # П1: поддержка по email, каждые 5 мин
    },
    "churn-retrain": {
        "task": "app.tasks.retrain_churn",
        "schedule": crontab(day_of_week=1, hour=5, minute=0),
    },
}
