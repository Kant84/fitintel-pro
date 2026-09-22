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
    "ml-dataset-dump": {
        "task": "app.tasks.dump_parquet",
        "schedule": crontab(hour=4, minute=0),  # E60: ночной дамп в Parquet
    },
        "churn-retrain": {
        "task": "app.tasks.retrain_churn",
        "schedule": crontab(day_of_week=1, hour=5, minute=0),
    },
}