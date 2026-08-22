"""FitIntel Pro — клиентское логирование (logs/client_YYYYMMDD.log)"""
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"client_{datetime.now():%Y%m%d}.log"

logger = logging.getLogger("fitintel")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

log = logger


def install_excepthook():
    def hook(exc_type, exc, tb):
        log.critical("UNHANDLED: %s", "".join(traceback.format_exception(exc_type, exc, tb)))
    sys.excepthook = hook
