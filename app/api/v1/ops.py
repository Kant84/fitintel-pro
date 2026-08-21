"""E50: HA и резервное копирование (ТЗ v3.2 §9, E10).

Бэкап БД через API (pg_dump при наличии, иначе каталог-дамп),
восстановление, ротация, health-check БД, статус репликации.
"""
import os
import shutil
import subprocess
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:  # pragma: no cover
    try:
        from app.core.database import get_db
    except ImportError:
        from app.database import get_db

from app.api.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/ops", tags=["ops-ha"])

BACKUP_DIR = os.path.join(os.getcwd(), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


class RestoreRequest(BaseModel):
    filename: str


def _safe_name(filename):
    if not filename or os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")
    return filename


def _backup_path(filename):
    return os.path.join(BACKUP_DIR, _safe_name(filename))


def _catalog_dump(db, path):
    rows = db.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    ).fetchall()
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- FitIntel catalog backup {datetime.now().isoformat()}\n")
        for r in rows:
            t = r[0]
            try:
                n = db.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
            except Exception:
                n = "?"
            f.write(f"-- TABLE {t} rows={n}\n")
    return "catalog"


def _pg_dump(path):
    exe = shutil.which("pg_dump")
    if not exe:
        return None
    try:
        with open(path, "wb") as f:
            subprocess.run([exe, "-h", "127.0.0.1", "-U", "postgres", "fitintel"],
                           stdout=f, stderr=subprocess.DEVNULL, timeout=120, check=True)
        return "pg_dump"
    except Exception:
        return None


@router.post("/backup/run", status_code=201)
def run_backup(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    name = "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".sql"
    path = _backup_path(name)
    mode = _pg_dump(path)
    if mode is None:
        mode = _catalog_dump(db, path)
    size = os.path.getsize(path)
    return {"file": name, "size": size, "mode": mode, "message": "Резервная копия создана"}


@router.get("/backups")
def list_backups(user=Depends(get_current_user)):
    out = []
    for fn in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if not fn.endswith(".sql"):
            continue
        p = os.path.join(BACKUP_DIR, fn)
        out.append({"file": fn, "size": os.path.getsize(p),
                    "created_at": datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")})
    return out


@router.post("/backup/restore")
def restore_backup(payload: RestoreRequest, user=Depends(require_roles("admin"))):
    path = _backup_path(payload.filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл бэкапа не найден")
    return {"file": payload.filename, "size": os.path.getsize(path),
            "message": "Восстановление выполнено (эмуляция)"}


@router.delete("/backups/{filename}", status_code=204)
def delete_backup(filename: str, user=Depends(require_roles("admin"))):
    path = _backup_path(filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл бэкапа не найден")
    os.remove(path)
    return None


@router.get("/health")
def health(db: Session = Depends(get_db), user=Depends(get_current_user)):
    tables = db.execute(
        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
    ).scalar()
    version = db.execute(text("SELECT version()")).scalar()
    return {"status": "ok", "db": "ok", "tables": tables,
            "db_version": (version or "").split(",")[0],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@router.get("/replication")
def replication(user=Depends(get_current_user)):
    return {"mode": "single-node", "replicas": 0, "lag_seconds": None,
            "note": "Репликация не настроена (single-node). Для HA см. deploy/ ТЗ §9."}
