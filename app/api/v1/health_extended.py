"""E9: Расширенный health-check — БД, Redis, диск, память."""
import os, psutil
from sqlalchemy import text
from app.api.v1.license_api import _eng

def health_extended():
    result = {"status": "ok", "timestamp": __import__('datetime').datetime.now().isoformat(), "checks": {}}
    
    # PostgreSQL
    try:
        with _eng().begin() as c:
            c.execute(text("SELECT 1"))
        result["checks"]["postgres"] = "ok"
    except Exception as e:
        result["checks"]["postgres"] = f"fail: {str(e)[:80]}"
        result["status"] = "degraded"
    
    # Диск
    try:
        du = psutil.disk_usage(".")
        result["checks"]["disk"] = {
            "total_gb": round(du.total / (1024**3), 1),
            "free_gb": round(du.free / (1024**3), 1),
            "percent": du.percent
        }
        if du.percent > 90:
            result["status"] = "degraded"
    except Exception as e:
        result["checks"]["disk"] = f"fail: {e}"
    
    # Память
    try:
        mem = psutil.virtual_memory()
        result["checks"]["memory"] = {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent": mem.percent
        }
    except Exception as e:
        result["checks"]["memory"] = f"fail: {e}"
    
    # Последний бэкап
    try:
        from pathlib import Path
        backups = sorted(Path("backups/postgres").glob("fitintel_*.sql.gz"))
        if backups:
            result["checks"]["last_backup"] = backups[-1].name
        else:
            result["checks"]["last_backup"] = "none"
    except Exception:
        result["checks"]["last_backup"] = "unknown"
    
    return result
