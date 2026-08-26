"""E7: Автобэкап PostgreSQL — pg_dump ежедневно 03:00, хранение 30 дней."""
import os, subprocess, gzip
from datetime import datetime, timedelta
from pathlib import Path

BACKUP_DIR = Path("backups/postgres")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
RETENTION_DAYS = 30

# Читаем из .env если есть
def _env(k, d=""):
    try:
        with open(".env", encoding="utf-8") as f:
            for line in f:
                if line.startswith(k + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return os.getenv(k, d)

DB_HOST = _env("POSTGRES_HOST", "127.0.0.1")
DB_PORT = _env("POSTGRES_PORT", "5432")
DB_NAME = _env("POSTGRES_DB", "fitnexus")
DB_USER = _env("POSTGRES_USER", "postgres")
DB_PASS = _env("POSTGRES_PASSWORD", "")

def backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = BACKUP_DIR / f"fitintel_{ts}.sql.gz"
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASS
    cmd = [
        "pg_dump",
        f"--host={DB_HOST}",
        f"--port={DB_PORT}",
        f"--username={DB_USER}",
        f"--dbname={DB_NAME}",
        "--format=plain",
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        stdout, stderr = proc.communicate(timeout=120)
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")[:300]
            print(f"[E7] pg_dump ERROR: {err}")
            return False
        with gzip.open(filename, "wb") as gz:
            gz.write(stdout)
        size = filename.stat().st_size
        print(f"[E7] Backup OK: {filename.name} ({size:,} bytes)")
        return True
    except Exception as e:
        print(f"[E7] Backup FAIL: {e}")
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
    print(f"[E7] Rotated: {removed} old backups removed")

if __name__ == "__main__":
    if backup():
        rotate()
