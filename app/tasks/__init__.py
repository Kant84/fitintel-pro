# app/tasks/__init__.py — Celery-задачи FitIntel Pro
from app.tasks.ml import dump_parquet  # noqa: F401

__all__ = ["dump_parquet"]