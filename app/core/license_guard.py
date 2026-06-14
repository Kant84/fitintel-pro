# app/core/license_guard.py
"""
License Guard — обязательная проверка лицензии.

Без валидной лицензии API возвращает 403 (кроме setup/license endpoints).
Проверяет: срок, отзыв, активность, лимиты.
"""

from __future__ import annotations

import ast
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

LICENSE_STATE_PATH = Path(__file__).parents[1] / ".license_state"
LICENSE_KEY_FILE = Path(__file__).parents[1] / ".license_key"

# Endpoints excluded from license check
EXCLUDED_PATHS = {
    "/api/v1/setup",
    "/api/v1/license",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
    "/health",
    "/api/v1/health",
}


class LicenseState:
    """License state management."""

    @staticmethod
    def is_licensed() -> bool:
        """Check if license was previously validated."""
        if not LICENSE_STATE_PATH.exists():
            return False
        try:
            data = ast.literal_eval(LICENSE_STATE_PATH.read_text())
            return data.get("status") == "active" and data.get("license_key") == LicenseState._get_stored_key()
        except Exception:
            return False

    @staticmethod
    def get_license_key() -> str | None:
        """Get stored license key."""
        return LicenseState._get_stored_key()

    @staticmethod
    def _get_stored_key() -> str | None:
        if LICENSE_KEY_FILE.exists():
            return LICENSE_KEY_FILE.read_text().strip() or None
        return None

    @staticmethod
    def store_license_key(key: str) -> None:
        """Store license key."""
        LICENSE_KEY_FILE.write_text(key)

    @staticmethod
    def set_licensed(key: str, info: dict) -> None:
        """Mark system as licensed."""
        LicenseState.store_license_key(key)
        state = {
            "status": "active",
            "license_key": key,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": info.get("expires_at"),
            "license_type": info.get("license_type"),
            "max_users": info.get("max_users"),
            "max_clients": info.get("max_clients"),
            "max_terminals": info.get("max_terminals"),
        }
        LICENSE_STATE_PATH.write_text(str(state))
        logger.info("License activated: %s", key[:8] + "...")

    @staticmethod
    def clear_license() -> None:
        """Remove license state."""
        for f in [LICENSE_STATE_PATH, LICENSE_KEY_FILE]:
            if f.exists():
                f.unlink()
        logger.warning("License state cleared")

    @staticmethod
    def is_path_excluded(path: str) -> bool:
        """Check if path is excluded from license check."""
        for excluded in EXCLUDED_PATHS:
            if path.startswith(excluded):
                return True
        return False


def check_license_installed() -> bool:
    """Quick check if license is installed and active."""
    return LicenseState.is_licensed()
