# app/tasks/__init__.py — Celery-задачи FitIntel Pro
from app.tasks.ml import dump_parquet  # noqa: F401
from app.tasks.email_queue import process_email_queue  # noqa: F401

__all__ = ["dump_parquet", "process_email_queue"]