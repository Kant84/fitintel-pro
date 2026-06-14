# app/middleware/license_middleware.py
"""
License Middleware — блокирует все API без валидной лицензии.

Исключения: setup wizard, license endpoints, docs, health check.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.license_guard import LicenseState

logger = logging.getLogger(__name__)


class LicenseMiddleware(BaseHTTPMiddleware):
    """Middleware that blocks API without valid license."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        path = request.url.path
        print(f"[LICENSE] path={path}, excluded={LicenseState.is_path_excluded(path)}, licensed={LicenseState.is_licensed()}")

        # Allow excluded paths without license
        if LicenseState.is_path_excluded(path):
            return await call_next(request)

        # Check license
        if not LicenseState.is_licensed():
            logger.warning("Blocked request to %s — no license", path)
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Требуется лицензия. Введите лицензионный ключ в панели настройки.",
                    "code": "LICENSE_REQUIRED",
                    "action_required": "Перейдите в Setup Wizard и введите лицензионный ключ",
                    "setup_url": "/api/v1/setup/license/activate",
                },
            )

        return await call_next(request)
