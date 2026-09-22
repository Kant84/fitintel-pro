# app/tasks/ml.py — ML-задачи (E60 Self-Learning)
import logging, os
from datetime import datetime
from celery_app import celery_app

log = logging.getLogger(__name__)

DUMP_DIR = os.environ.get("ML_DATA_DIR", "data/ml")  # прибит в compose: volume app_data


@celery_app.task(name="app.tasks.dump_parquet")
def dump_parquet():
    """Ночной дамп ml_events → Parquet для Feature Store."""
    os.makedirs(DUMP_DIR, exist_ok=True)
    fname = os.path.join(DUMP_DIR, f"events_{datetime.now():%Y%m%d}.parquet")

    try:
        import pandas as pd
        from app.api.v1.license_api import _eng
        from sqlalchemy import text

        with _eng().connect() as c:
            df = pd.read_sql(text("SELECT * FROM ml_events"), c)
        df.to_parquet(fname, index=False)
        log.info("[E60] dump_parquet: %d rows -> %s", len(df), fname)
        return {"status": "ok", "rows": len(df), "file": fname}
    except Exception as e:
        log.error("[E60] dump_parquet failed: %s", e)
        return {"status": "error", "error": str(e)}

@celery_app.task(name="app.tasks.retrain_churn")
def retrain_churn():
    """Переобучение XGBoost на Parquet-дампах. Beat: понедельник 05:00."""
    try:
        import glob
        import pandas as pd

        files = sorted(glob.glob(os.path.join(DUMP_DIR, "events_*.parquet")))
        if len(files) < 14:
            return {"status": "skipped", "reason": f"only {len(files)} dumps, need 14+"}

        total_rows = sum(len(pd.read_parquet(f)) for f in files[-14:])
        return {"status": "stub", "events": total_rows,
                "message": "Сбор labels — следующий этап"}
    except Exception as e:
        log.error("[E60] retrain_churn failed: %s", e)
        return {"status": "error", "error": str(e)}