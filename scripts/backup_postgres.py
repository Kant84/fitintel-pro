"""E7: Автобэкап PostgreSQL — ежедневно 03:00, хранение 30 дней.

Где запускать:
  • ХОСТ (рекомендуется, cron клуба):  python scripts/backup_postgres.py
      — дамп делает контейнер db (там есть pg_dump нужной версии).
  • Внутри контейнера api (планировщик): напрямую через pg_dump, если он установлен;
      иначе честно сообщает, что бэкап делает хост.

Дампы: $BACKUP_DIR (по умолчанию ./backups рядом с репо на хосте,
/app/data/backups в контейнере — в обоих случаях переживают пересборку).
"""
import os
import subprocess
import gzip
from datetime import datetime, timedelta
from pathlib import Path

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/app/data/backups"))
RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))

REPO_ROOT = Path(__file__).resolve().parents[1]


def _env(k, d=""):
    for candidate in (REPO_ROOT / "deploy" / ".env", REPO_ROOT / ".env", Path("/app/.env")):
        try:
            with open(candidate, encoding="utf-8") as f:
                for line in f:
                    if line.startswith(k + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return os.getenv(k, d)


DB_HOST = _env("POSTGRES_HOST", "db")
DB_PORT = _env("POSTGRES_PORT", "5432")
DB_NAME = _env("POSTGRES_DB", "fitnexus_ai")
DB_USER = _env("POSTGRES_USER", "fitnexus_user")
DB_PASS = _env("POSTGRES_PASSWORD", "")


def _dump_via_docker() -> bytes:
    """Хост: дамп через контейнер db (pg_dump нужной версии там всегда есть)."""
    for name in ("docker-compose.prod.yml", "docker-compose.test.yml"):
        cf = REPO_ROOT / "deploy" / name
        if cf.exists():
            break
    else:
        raise RuntimeError("compose-файл не найден в deploy/")
    r = subprocess.run(
        ["docker", "compose", "-f", str(cf), "exec", "-T", "db",
         "pg_dump", "-U", DB_USER, DB_NAME],
        capture_output=True, timeout=600,
        env={**os.environ, "PGPASSWORD": DB_PASS})
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:300])
    return r.stdout


def _dump_direct() -> bytes:
    """Внутри контейнера api: прямой pg_dump (если установлен в образе)."""
    env = {**os.environ, "PGPASSWORD": DB_PASS}
    r = subprocess.run(
        ["pg_dump", f"--host={DB_HOST}", f"--port={DB_PORT}",
         f"--username={DB_USER}", f"--dbname={DB_NAME}", "--format=plain"],
        capture_output=True, timeout=600, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:300])
    return r.stdout


def _dump() -> bytes:
    try:
        return _dump_direct()
    except FileNotFoundError:
        return _dump_via_docker()


def backup() -> bool:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = BACKUP_DIR / f"fitintel_{ts}.sql.gz"
    try:
        data = _dump()
        with gzip.open(filename, "wb") as gz:
            gz.write(data)
        os.chmod(filename, 0o600)
        print(f"[E7] Backup OK: {filename} ({filename.stat().st_size:,} bytes)")
        return True
    except Exception as e:
        print(f"[E7] Backup FAIL: {e}")
        print("[E7] Проверьте: docker запущен? На хосте выполните "
              "`python scripts/backup_postgres.py` (рекомендуется) или "
              "`bash scripts/backup.sh`.")
        return False


def rotate():
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0
    for f in BACKUP_DIR.glob("fitintel_*.sql.gz"):
        try:
            ts_str = f.stem.split("_")[1] + "_" + f.stem.split("_")[2]
            ft = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            if ft < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass
    print(f"[E7] Rotated: {removed} old backups removed (keep {RETENTION_DAYS} days)")


def main():
    if backup():
        rotate()


if __name__ == "__main__":
    main()