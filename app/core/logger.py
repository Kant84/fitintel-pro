"""Production logging — file + console with rotation (Linux-style)."""
import logging, logging.handlers, os, sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

APP_LOG = LOG_DIR / "app.log"
ERROR_LOG = LOG_DIR / "error.log"
ACCESS_LOG = LOG_DIR / "access.log"

# Linux-style format: 2024-08-26 14:32:01,453 [INFO] app.main: message
FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"

def setup_logging(level: str = "INFO"):
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(FMT, DATE_FMT))
    root.addHandler(console)

    # App log (rotating, 10 MB x 5 backups)
    app_handler = logging.handlers.RotatingFileHandler(
        APP_LOG, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )
    app_handler.setFormatter(logging.Formatter(FMT, DATE_FMT))
    root.addHandler(app_handler)

    # Error log (rotating, 10 MB x 3 backups, WARNING+)
    err_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG, maxBytes=10*1024*1024, backupCount=3, encoding="utf-8"
    )
    err_handler.setLevel(logging.WARNING)
    err_handler.setFormatter(logging.Formatter(FMT, DATE_FMT))
    root.addHandler(err_handler)

    # Uvicorn access log -> file
    access_handler = logging.handlers.RotatingFileHandler(
        ACCESS_LOG, maxBytes=10*1024*1024, backupCount=3, encoding="utf-8"
    )
    access_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", DATE_FMT))
    logging.getLogger("uvicorn.access").addHandler(access_handler)
    logging.getLogger("uvicorn.access").propagate = False

    # SQLAlchemy echo off in prod
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root
