# app/api/v1/setup.py
"""
Setup Wizard API — superadmin-only system configuration panel.

Step 1 (REQUIRED): License activation — software won't work without it!
Step 2: Database, Redis, Security settings
Step 3: Integrations (Email, SMS, MAX, Telegram, 1C)
Step 4: Test connections & complete setup
"""

from __future__ import annotations

import ast
import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.dependencies import require_permission
from app.core.config import settings
from app.core.license_guard import LicenseState, LICENSE_STATE_PATH
from app.db.session import get_db
from app.services.license_service import LicenseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup Wizard"])

ENV_PATH = Path(__file__).parents[3] / ".env"
ENV_EXAMPLE_PATH = Path(__file__).parents[3] / ".env.example"
SETUP_STATE_PATH = Path(__file__).parents[3] / ".setup_state"

# ═══════════════════════════════════════════════
# STEP 1: LICENSE (REQUIRED — blocks everything)
# ═══════════════════════════════════════════════


class LicenseActivateRequest(BaseModel):
    license_key: str = Field(..., min_length=8, description="License key from vendor")
    device_id: str = Field(default="", description="Device identifier")


class LicenseActivateResponse(BaseModel):
    status: str
    license_key: str | None = None
    license_type: str | None = None
    expires_at: str | None = None
    max_users: int | None = None
    max_clients: int | None = None
    max_terminals: int | None = None
    detail: str | None = None


class LicenseStatusResponse(BaseModel):
    is_licensed: bool
    license_key: str | None = None
    license_type: str | None = None
    expires_at: str | None = None
    days_remaining: int | None = None
    max_users: int | None = None
    max_clients: int | None = None
    max_terminals: int | None = None


class LicenseCheckLimitsResponse(BaseModel):
    users: dict[str, int]
    clients: dict[str, int]
    terminals: dict[str, int]


# ── License endpoints ───────────────────────


@router.get("/license/status", response_model=LicenseStatusResponse)
async def get_license_status() -> dict[str, Any]:
    """Check current license status (no auth required — needed for initial setup)."""
    is_licensed = LicenseState.is_licensed()
    key = LicenseState.get_license_key()
    if not is_licensed or not key:
        return {"is_licensed": False}


    try:
        state = ast.literal_eval(LICENSE_STATE_PATH.read_text())
        expires = state.get("expires_at", "")
        days_remaining = None
        if expires:
            from datetime import datetime
            expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            days_remaining = max(0, (expires_dt - datetime.now(timezone.utc)).days)
        return {
            "is_licensed": True,
            "license_key": key[:8] + "...",
            "license_type": state.get("license_type"),
            "expires_at": expires,
            "days_remaining": days_remaining,
            "max_users": state.get("max_users"),
            "max_clients": state.get("max_clients"),
            "max_terminals": state.get("max_terminals"),
        }
    except Exception:
        return {"is_licensed": False}


@router.post("/license/activate", response_model=LicenseActivateResponse)
async def activate_license(
    req: LicenseActivateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Activate license — REQUIRED FIRST STEP.

    Without this, software returns 403 on all API calls.
    Validates license key against database, stores state.
    """
    service = LicenseService(db)

    # Use machine identifier if device_id not provided
    device_id = req.device_id or _get_machine_id()

    valid, message, info = service.verify_license(req.license_key, device_id)

    if not valid:
        logger.warning("License activation failed: %s", message)
        raise HTTPException(status_code=400, detail=message)

    # Store license state
    LicenseState.set_licensed(req.license_key, info)

    logger.info("License activated: type=%s, expires=%s", info.get("license_type"), info.get("expires_at"))

    return LicenseActivateResponse(
        status="activated",
        license_key=req.license_key[:8] + "...",
        license_type=info.get("license_type"),
        expires_at=info.get("expires_at"),
        max_users=info.get("max_users"),
        max_clients=info.get("max_clients"),
        max_terminals=info.get("max_terminals"),
        detail="Лицензия активирована. Перезагрузите страницу.",
    )


@router.post("/license/deactivate")
async def deactivate_license(
    _: Any = Depends(require_permission("settings.update")),
) -> dict[str, str]:
    """Deactivate current license (requires admin)."""
    LicenseState.clear_license()
    return {"status": "deactivated", "detail": "Лицензия деактивирована. ПО заблокировано."}


@router.get("/license/limits", response_model=LicenseCheckLimitsResponse)
async def get_license_limits(
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission("settings.read")),
) -> dict[str, Any]:
    """Get current usage vs license limits."""
    is_licensed = LicenseState.is_licensed()
    key = LicenseState.get_license_key()
    if not is_licensed or not key:
        raise HTTPException(status_code=403, detail="No active license")
    service = LicenseService(db)
    return service.check_system_limits(key)


# ═══════════════════════════════════════════════
# STEP 2-4: ENV Settings (after license)
# ═══════════════════════════════════════════════


class SetupStatusResponse(BaseModel):
    setup_required: bool = True
    steps: list = []
    current_step: str | None = None
    is_complete: bool
    is_licensed: bool
    is_first_run: bool
    completed_at: str | None = None
    env_exists: bool
    total_settings: int = 0


class EnvSettingItem(BaseModel):
    key: str
    value: str
    description: str
    category: str
    is_sensitive: bool = False
    is_required: bool = False


class SettingUpdateRequest(BaseModel):
    key: str
    value: str


class BulkUpdateRequest(BaseModel):
    settings: dict[str, str]


class TestConnectionRequest(BaseModel):
    type: str


class TestConnectionResponse(BaseModel):
    type: str
    status: str
    detail: str | None = None
    response_time_ms: int | None = None


class SetupCompleteRequest(BaseModel):
    confirmed: bool = True


# ── Category maps ───────────────────────────

CATEGORY_MAP = {
    "APP_NAME": "general", "APP_ENV": "general", "APP_DEBUG": "general",
    "APP_HOST": "general", "APP_PORT": "general", "API_DOMAIN": "general",
    "DOCS_ENABLED": "general", "MAINTENANCE_MODE": "general",
    "SECRET_KEY": "security", "JWT_ALGORITHM": "security",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "security", "REFRESH_TOKEN_EXPIRE_DAYS": "security",
    "POSTGRES_HOST": "database", "POSTGRES_PORT": "database",
    "POSTGRES_DB": "database", "POSTGRES_USER": "database", "POSTGRES_PASSWORD": "database",
    "REDIS_HOST": "redis", "REDIS_PORT": "redis", "REDIS_DB": "redis", "REDIS_PASSWORD": "redis",
    "BACKEND_CORS_ORIGINS": "cors",
    "CELERY_BROKER_URL": "celery", "CELERY_RESULT_BACKEND": "celery",
    "SENTRY_DSN": "monitoring",
    "SMTP_HOST": "email", "SMTP_PORT": "email", "SMTP_USER": "email",
    "SMTP_PASSWORD": "email", "SMTP_TLS": "email", "SMTP_FROM_NAME": "email", "SMTP_FROM_EMAIL": "email",
    "SMS_PROVIDER": "sms", "SMS_API_KEY": "sms", "SMS_API_SECRET": "sms", "SMS_SENDER": "sms",
    "TELEGRAM_BOT_TOKEN": "telegram",
    "MAX_BOT_TOKEN": "max", "MAX_API_URL": "max",
    "ONE_C_API_URL": "one_c", "ONE_C_API_KEY": "one_c",
    "WEBHOOK_URL": "webhooks", "WEBHOOK_SECRET": "webhooks",
}

DESCRIPTION_MAP = {
    "APP_NAME": "Название приложения", "APP_ENV": "Среда (dev/test/prod)",
    "APP_DEBUG": "Режим отладки (true/false)", "APP_HOST": "Хост для запуска",
    "APP_PORT": "Порт приложения", "API_DOMAIN": "Внешний URL API",
    "DOCS_ENABLED": "Swagger/ReDoc документация", "MAINTENANCE_MODE": "Режим обслуживания",
    "SECRET_KEY": "Секретный ключ JWT", "JWT_ALGORITHM": "Алгоритм JWT",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "TTL access токена (мин)", "REFRESH_TOKEN_EXPIRE_DAYS": "TTL refresh токена (дни)",
    "POSTGRES_HOST": "Хост PostgreSQL", "POSTGRES_PORT": "Порт PostgreSQL",
    "POSTGRES_DB": "Имя базы данных", "POSTGRES_USER": "Пользователь БД", "POSTGRES_PASSWORD": "Пароль БД",
    "REDIS_HOST": "Хост Redis", "REDIS_PORT": "Порт Redis",
    "REDIS_DB": "Номер БД Redis", "REDIS_PASSWORD": "Пароль Redis",
    "BACKEND_CORS_ORIGINS": "Разрешённые CORS origins",
    "CELERY_BROKER_URL": "URL брокера Celery", "CELERY_RESULT_BACKEND": "URL хранилища результатов Celery",
    "SENTRY_DSN": "DSN для Sentry",
    "SMTP_HOST": "SMTP сервер", "SMTP_PORT": "SMTP порт",
    "SMTP_USER": "SMTP логин", "SMTP_PASSWORD": "SMTP пароль",
    "SMTP_TLS": "Использовать TLS", "SMTP_FROM_NAME": "Имя отправителя", "SMTP_FROM_EMAIL": "Email отправителя",
    "SMS_PROVIDER": "SMS провайдер (smsc/smsru/twilio)", "SMS_API_KEY": "API ключ SMS",
    "SMS_API_SECRET": "API секрет SMS", "SMS_SENDER": "Имя отправителя SMS",
    "TELEGRAM_BOT_TOKEN": "Токен Telegram бота",
    "MAX_BOT_TOKEN": "Токен MAX Messenger бота", "MAX_API_URL": "URL MAX API",
    "ONE_C_API_URL": "URL API 1С", "ONE_C_API_KEY": "Ключ API 1С",
    "WEBHOOK_URL": "URL для вебхуков", "WEBHOOK_SECRET": "Секрет вебхуков",
}

SENSITIVE_KEYS = {
    "SECRET_KEY", "POSTGRES_PASSWORD", "REDIS_PASSWORD",
    "SMTP_PASSWORD", "SMS_API_KEY", "SMS_API_SECRET",
    "TELEGRAM_BOT_TOKEN", "MAX_BOT_TOKEN", "ONE_C_API_KEY",
    "SENTRY_DSN", "WEBHOOK_SECRET",
}

REQUIRED_KEYS = {
    "APP_NAME", "SECRET_KEY", "POSTGRES_HOST", "POSTGRES_PORT",
    "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "REDIS_HOST", "REDIS_PORT",
}

CATEGORY_LABELS = {
    "general": "Общие настройки", "security": "Безопасность",
    "database": "PostgreSQL база данных", "redis": "Redis кэш",
    "cors": "CORS", "celery": "Celery фоновые задачи",
    "monitoring": "Мониторинг", "email": "Email SMTP",
    "sms": "SMS уведомления", "telegram": "Telegram бот",
    "max": "MAX Messenger", "one_c": "1С интеграция",
    "webhooks": "Webhooks",
}


# ── Helpers ─────────────────────────────────


def read_env_file(path: Path) -> dict[str, str]:
    values = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip()
    return values


def write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = []
    if ENV_EXAMPLE_PATH.exists():
        with open(ENV_EXAMPLE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, _, _ = stripped.partition("=")
                    key = key.strip()
                    if key in values:
                        lines.append(f"{key}={values[key]}\n")
                        continue
                lines.append(line)
    else:
        for key, value in sorted(values.items()):
            lines.append(f"{key}={value}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def get_masked_value(key: str, value: str) -> str:
    if key in SENSITIVE_KEYS and value:
        if len(value) <= 8:
            return "****"
        return value[:4] + "****" + value[-4:]
    return value


def _get_machine_id() -> str:
    """Get unique machine identifier."""
    import platform
    return hashlib.sha256(f"{platform.node()}:{platform.machine()}".encode()).hexdigest()[:16]


# ── Setup status ────────────────────────────


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(
    _: Any = Depends(require_permission("settings.read")),
) -> dict[str, Any]:
    """Get overall setup status."""
    is_complete = SETUP_STATE_PATH.exists()
    completed_at = None
    if is_complete:
        try:
            completed_at = SETUP_STATE_PATH.read_text().strip()
        except Exception:
            pass
    env_values = read_env_file(ENV_PATH)
    wdb = next(get_db())
    try:
        wdone = _wizard_get(wdb, "setup_complete") == "true"
        wsteps = _wizard_steps(wdb)
    finally:
        wdb.close()
    return {
        "is_complete": is_complete,
        "is_licensed": LicenseState.is_licensed(),
        "is_first_run": not is_complete,
        "completed_at": completed_at,
        "env_exists": ENV_PATH.exists(),
        "total_settings": len(env_values),
        "setup_required": not wdone,
        "steps": wsteps["steps"],
        "current_step": wsteps["current_step"],
    }


# ── Categories ──────────────────────────────


@router.get("/categories")
async def get_categories(
    _: Any = Depends(require_permission("settings.read")),
) -> dict[str, list[dict[str, str]]]:
    """Get setting categories with labels and icons."""
    icons = {
        "general": "settings", "security": "shield", "database": "database",
        "redis": "layers", "cors": "globe", "celery": "clock",
        "monitoring": "activity", "email": "mail", "sms": "message-square",
        "telegram": "send", "max": "bell", "one_c": "briefcase", "webhooks": "link",
    }
    return {
        "categories": [
            {"key": k, "label": v, "icon": icons.get(k, "circle")}
            for k, v in CATEGORY_LABELS.items()
        ]
    }


# ── Settings CRUD ───────────────────────────


@router.get("/settings", response_model=dict)
async def get_all_settings(
    _: Any = Depends(require_permission("settings.read")),
) -> dict[str, Any]:
    """Get all .env settings organized by category."""
    values = read_env_file(ENV_PATH)
    settings_list = []
    seen = set()
    for key in CATEGORY_MAP:
        if key in seen:
            continue
        seen.add(key)
        raw_value = values.get(key, "")
        settings_list.append({
            "key": key,
            "value": get_masked_value(key, raw_value) if raw_value else "",
            "description": DESCRIPTION_MAP.get(key, key),
            "category": CATEGORY_MAP[key],
            "is_sensitive": key in SENSITIVE_KEYS,
            "is_required": key in REQUIRED_KEYS,
        })
    return {
        "settings": settings_list,
        "categories": list(dict.fromkeys(CATEGORY_MAP.values())),
    }


@router.get("/settings/{category}")
async def get_settings_by_category(
    category: str,
    _: Any = Depends(require_permission("settings.read")),
) -> dict[str, Any]:
    """Get settings for a specific category."""
    all_data = await get_all_settings(_)
    filtered = [s for s in all_data["settings"] if s["category"] == category]
    return {"settings": filtered, "categories": [category]}


@router.get("/setting/{key}")
async def get_setting_value(
    key: str,
    _: Any = Depends(require_permission("settings.read")),
) -> dict[str, str]:
    """Get single setting value (unmasked for editing)."""
    values = read_env_file(ENV_PATH)
    if key not in values:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    return {"key": key, "value": values[key]}


@router.put("/setting")
async def update_setting(
    req: SettingUpdateRequest,
    _: Any = Depends(require_permission("settings.update")),
) -> dict[str, str]:
    """Update a single .env setting."""
    values = read_env_file(ENV_PATH)
    values[req.key] = req.value
    write_env_file(ENV_PATH, values)
    logger.info("Setting updated: %s", req.key)
    return {"status": "updated", "key": req.key}


@router.put("/settings/bulk")
async def update_settings_bulk(
    req: BulkUpdateRequest,
    _: Any = Depends(require_permission("settings.update")),
) -> dict[str, Any]:
    """Update multiple .env settings at once."""
    values = read_env_file(ENV_PATH)
    updated = []
    for key, value in req.settings.items():
        if key in CATEGORY_MAP:
            values[key] = value
            updated.append(key)
    write_env_file(ENV_PATH, values)
    logger.info("Bulk settings updated: %d keys", len(updated))
    return {"status": "updated", "keys_updated": len(updated), "keys": updated}


# ── Connection testing ──────────────────────


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    req: TestConnectionRequest,
    _: Any = Depends(require_permission("settings.update")),
) -> dict[str, Any]:
    """Test connection to external service."""
    import socket
    import time

    start = int(time.time() * 1000)
    values = read_env_file(ENV_PATH)

    if req.type == "postgres":
        host = values.get("POSTGRES_HOST", settings.POSTGRES_HOST)
        port = int(values.get("POSTGRES_PORT", settings.POSTGRES_PORT))
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            return {"type": "postgres", "status": "ok", "detail": f"Connected to {host}:{port}", "response_time_ms": int(time.time() * 1000) - start}
        except Exception as e:
            return {"type": "postgres", "status": "error", "detail": str(e), "response_time_ms": int(time.time() * 1000) - start}

    elif req.type == "redis":
        host = values.get("REDIS_HOST", settings.REDIS_HOST)
        port = int(values.get("REDIS_PORT", settings.REDIS_PORT))
        try:
            import redis
            r = redis.Redis(host=host, port=port, socket_timeout=5)
            r.ping()
            return {"type": "redis", "status": "ok", "detail": f"PONG from {host}:{port}", "response_time_ms": int(time.time() * 1000) - start}
        except Exception as e:
            return {"type": "redis", "status": "error", "detail": str(e), "response_time_ms": int(time.time() * 1000) - start}

    elif req.type == "smtp":
        host = values.get("SMTP_HOST", "")
        port = int(values.get("SMTP_PORT", "587"))
        if not host:
            return {"type": "smtp", "status": "error", "detail": "SMTP_HOST not configured"}
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            return {"type": "smtp", "status": "ok", "detail": f"SMTP reachable at {host}:{port}", "response_time_ms": int(time.time() * 1000) - start}
        except Exception as e:
            return {"type": "smtp", "status": "error", "detail": str(e), "response_time_ms": int(time.time() * 1000) - start}

    elif req.type == "max":
        token = values.get("MAX_BOT_TOKEN", settings.MAX_BOT_TOKEN)
        if not token:
            return {"type": "max", "status": "error", "detail": "MAX_BOT_TOKEN not set"}
        try:
            import json, urllib.request
            url = f"https://api.max.ru/bot{token}/getMe"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if data.get("ok"):
                    bot = data.get("result", {})
                    return {"type": "max", "status": "ok", "detail": f"Bot @{bot.get('username', 'unknown')}", "response_time_ms": int(time.time() * 1000) - start}
                return {"type": "max", "status": "error", "detail": data.get("description", "Error"), "response_time_ms": int(time.time() * 1000) - start}
        except Exception as e:
            return {"type": "max", "status": "error", "detail": str(e), "response_time_ms": int(time.time() * 1000) - start}

    elif req.type == "sms":
        provider = values.get("SMS_PROVIDER", settings.SMS_PROVIDER)
        api_key = values.get("SMS_API_KEY", settings.SMS_API_KEY)
        if not api_key:
            return {"type": "sms", "status": "error", "detail": "SMS_API_KEY not set"}
        return {"type": "sms", "status": "ok", "detail": f"Provider: {provider}", "response_time_ms": int(time.time() * 1000) - start}

    elif req.type == "telegram":
        token = values.get("TELEGRAM_BOT_TOKEN", settings.TELEGRAM_BOT_TOKEN)
        if not token:
            return {"type": "telegram", "status": "error", "detail": "TELEGRAM_BOT_TOKEN not set"}
        return {"type": "telegram", "status": "ok", "detail": "Token configured"}

    elif req.type == "one_c":
        url = values.get("ONE_C_API_URL", settings.ONE_C_API_URL)
        if not url:
            return {"type": "one_c", "status": "error", "detail": "ONE_C_API_URL not set"}
        try:
            import urllib.request
            req_obj = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req_obj, timeout=5):
                return {"type": "one_c", "status": "ok", "detail": f"1C reachable at {url}", "response_time_ms": int(time.time() * 1000) - start}
        except Exception as e:
            return {"type": "one_c", "status": "error", "detail": str(e), "response_time_ms": int(time.time() * 1000) - start}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown type: {req.type}")


# ── Complete setup ──────────────────────────


@router.post("/complete")
async def complete_setup(
    req: SetupCompleteRequest,
    _: Any = Depends(require_permission("settings.update")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mark setup wizard as complete."""
    # Require license first
    if not (LicenseState.is_licensed() or _db_license_active(db)):
        raise HTTPException(
            status_code=403,
            detail="Невозможно завершить настройку без лицензии. Сначала активируйте лицензию.",
        )

    if req.confirmed:
        now = datetime.now(timezone.utc).isoformat()
        SETUP_STATE_PATH.write_text(now)
        logger.info("Setup wizard completed at %s", now)
        _wizard_set(db, "step_complete", "true")
        _wizard_set(db, "setup_complete", "true")
        db.commit()
        return {"status": "completed", "timestamp": now,
                "setup_complete": True, "redirect_to_dashboard": True,
                "dashboard_url": "/dashboard"}
    return {"status": "cancelled"}


# ═══════════════════════════════════════════════
# STEP 1.5: Database init (after license)
# ═══════════════════════════════════════════════


@router.post("/database/init")
async def initialize_database(
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission("settings.update")),
) -> dict[str, Any]:
    """Run database migrations and seed initial data."""
    if not LicenseState.is_licensed():
        raise HTTPException(status_code=403, detail="Требуется лицензия")

    try:
        # Check if tables exist by querying
        from app.models import User
        count = db.query(User).count()
        return {
            "status": "ok",
            "detail": f"Database connected. Users table has {count} rows.",
            "seeded": False,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e), "suggestion": "Run: alembic upgrade head"}


@router.post("/database/seed")


# ═══════════════════════════════════════════════
# STEP 0: INIT (first-time setup check)
# ═══════════════════════════════════════════════


class InitSetupRequest(BaseModel):
    admin_login: str = Field(..., min_length=3, description='Superadmin login')
    admin_password: str = Field(..., min_length=8, description='Superadmin password')
    club_name: str = Field(default='FitIntel Club', description='Club name')


class InitSetupResponse(BaseModel):
    setup_complete: bool
    message: str


@router.post('/init', response_model=InitSetupResponse)
def init_setup(
    payload: InitSetupRequest,
    db: Session = Depends(get_db),
):
    """
    First-time setup initialization.
    Creates superadmin and marks setup as complete.
    """
    # check if setup is already done
    if SETUP_STATE_PATH.exists():
        raise HTTPException(status_code=409, detail='Setup already completed')
    
    # create admin user
    from app.services.auth_service import AuthService
    auth_service = AuthService(db)
    try:
        auth_service.create_user(payload.admin_login, payload.admin_password)
    except HTTPException:
        pass  # user already exists
    
    # mark setup as complete
    SETUP_STATE_PATH.write_text('completed')
    
    return InitSetupResponse(
        setup_complete=True,
        message='Setup completed successfully'
    )

async def seed_database(
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission("settings.update")),
) -> dict[str, Any]:
    """Seed database with initial roles, permissions, admin user."""
    if not LicenseState.is_licensed():
        raise HTTPException(status_code=403, detail="Требуется лицензия")

    try:
        from app.db.seed.seed_roles import seed_roles
        from app.db.seed.seed_permissions import seed_permissions
        from app.db.seed.seed_admin import seed_admin

        seed_roles(db)
        seed_permissions(db)
        seed_admin(db)

        return {"status": "seeded", "detail": "Roles, permissions, and admin user created"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
# ═══════════════════════════════════════════════
# E30: Setup Wizard — пошаговая настройка (setup_wizard в БД)
# ═══════════════════════════════════════════════

import json as _json
import uuid as _uuid

from fastapi import UploadFile, File
from app.api.dependencies import require_roles

WIZARD_STEPS = ["database", "license", "admin", "club", "devices", "tariffs", "complete"]


def _wizard_get(db: Session, key: str):
    row = db.execute(text("SELECT value FROM setup_wizard WHERE key = :k"), {"k": key}).fetchone()
    return row[0] if row else None


def _wizard_set(db: Session, key: str, value: str):
    db.execute(text(
        "INSERT INTO setup_wizard (key, value, updated_at) VALUES (:k, :v, :n) "
        "ON CONFLICT (key) DO UPDATE SET value = :v, updated_at = :n"
    ), {"k": key, "v": value, "n": datetime.now(timezone.utc)})


def _wizard_steps(db: Session):
    steps = [{"step": s, "done": _wizard_get(db, f"step_{s}") == "true"} for s in WIZARD_STEPS]
    current = next((s["step"] for s in steps if not s["done"]), "complete")
    return {"steps": steps, "current_step": current}


def _db_license_active(db: Session) -> bool:
    try:
        row = db.execute(text("SELECT expires_at FROM licenses ORDER BY id LIMIT 1")).fetchone()
        return bool(row and row[0] and row[0] > datetime.now(timezone.utc))
    except Exception:
        return False


def _require_step(db: Session, key: str, message: str):
    if _wizard_get(db, key) != "true":
        raise HTTPException(status_code=400, detail=message)


class DbConfigRequest(BaseModel):
    db_config: dict = {}


class SetupLicenseRequest(BaseModel):
    license_key: str


class SetupAdminRequest(BaseModel):
    email: str
    password: str
    login: str | None = None


@router.post("/database")
def setup_database(
    payload: DbConfigRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.2 — шаг 1: настройка БД"""
    db.execute(text("SELECT 1"))
    _wizard_set(db, "step_database", "true")
    db.commit()
    return {"message": "БД настроена", "next_step": "license"}


@router.post("/license")
def setup_license(
    payload: SetupLicenseRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.3 — шаг 2: активация лицензии"""
    _require_step(db, "step_database", "Сначала настройте БД")
    from app.routers.license import _validate_key
    if not _validate_key(payload.license_key):
        raise HTTPException(status_code=400, detail="Невалидный ключ лицензии")
    _wizard_set(db, "step_license", "true")
    db.commit()
    return {"message": "Лицензия активирована", "next_step": "admin"}


@router.post("/admin", status_code=201)
def setup_admin(
    payload: SetupAdminRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.4/E30.9 — шаг 3: создание SuperAdmin"""
    _require_step(db, "step_license", "Сначала активируйте лицензию")
    username = payload.login or payload.email
    exists = db.execute(text(
        "SELECT 1 FROM users WHERE email = :e OR username = :u"
    ), {"e": payload.email, "u": username}).fetchone()
    if exists:
        raise HTTPException(status_code=409, detail="Пользователь уже существует")
    from app.core.security import get_password_hash
    now = datetime.now(timezone.utc)
    db.execute(text(
        "INSERT INTO users (id, email, username, password_hash, is_active, "
        "is_superuser, is_verified, is_fired, failed_login_count, created_at, updated_at) "
        "VALUES (:i, :e, :u, :p, true, true, true, false, 0, :n, :n)"
    ), {"i": str(_uuid.uuid4()), "e": payload.email, "u": username,
        "p": get_password_hash(payload.password), "n": now})
    _wizard_set(db, "step_admin", "true")
    db.commit()
    return {"message": "SuperAdmin создан", "next_step": "club", "email": payload.email}

class ClubRequest(BaseModel):
    name: str
    address: str = ""
    timezone: str = "Europe/Moscow"


class DevicesRequest(BaseModel):
    devices: list = []


class TariffsRequest(BaseModel):
    tariffs: list = []


class ValidateConfigRequest(BaseModel):
    config: dict


class ResetRequest(BaseModel):
    confirmation: bool = False


@router.post("/club")
def setup_club(
    payload: ClubRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.5 — шаг 4: настройка клуба"""
    _require_step(db, "step_admin", "Сначала создайте администратора")
    _wizard_set(db, "club", _json.dumps(payload.model_dump(), ensure_ascii=False))
    _wizard_set(db, "step_club", "true")
    db.commit()
    return {"message": "Клуб настроен", "next_step": "devices"}


@router.post("/devices")
def setup_devices(
    payload: DevicesRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.6 — шаг 5: настройка устройств"""
    _require_step(db, "step_club", "Сначала настройте клуб")
    _wizard_set(db, "devices", _json.dumps(payload.devices, ensure_ascii=False))
    _wizard_set(db, "step_devices", "true")
    db.commit()
    return {"message": "Устройства настроены", "next_step": "tariffs",
            "devices_count": len(payload.devices)}


@router.post("/tariffs")
def setup_tariffs(
    payload: TariffsRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.7 — шаг 6: настройка тарифов"""
    _require_step(db, "step_devices", "Сначала настройте устройства")
    _wizard_set(db, "tariffs", _json.dumps(payload.tariffs, ensure_ascii=False))
    _wizard_set(db, "step_tariffs", "true")
    db.commit()
    return {"message": "Тарифы настроены", "next_step": "complete",
            "tariffs_count": len(payload.tariffs)}


@router.post("/import")
async def setup_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.11 — импорт настроек из файла"""
    content = await file.read()
    try:
        data = _json.loads(content.decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Невалидный файл настроек")
    _wizard_set(db, "imported_settings", _json.dumps(data, ensure_ascii=False))
    db.commit()
    return {"message": "Настройки импортированы",
            "imported_keys": len(data) if isinstance(data, dict) else 1}


@router.get("/export")
def setup_export(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.12 — экспорт настроек"""
    rows = db.execute(text("SELECT key, value FROM setup_wizard")).fetchall()
    return {"settings": {r[0]: r[1] for r in rows},
            "exported_at": datetime.now(timezone.utc).isoformat(), "version": "1.0"}


@router.post("/validate")
def setup_validate(payload: ValidateConfigRequest):
    """E30.13/E30.14 — валидация конфигурации"""
    errors = []
    cfg = payload.config or {}
    for key in ("database", "license", "admin", "club"):
        if key not in cfg:
            errors.append(f"Отсутствует секция: {key}")
    if isinstance(cfg.get("database"), dict) and not cfg["database"].get("host"):
        errors.append("database.host обязателен")
    if isinstance(cfg.get("license"), dict) and not cfg["license"].get("license_key"):
        errors.append("license.license_key обязателен")
    if isinstance(cfg.get("admin"), dict) and not cfg["admin"].get("email"):
        errors.append("admin.email обязателен")
    if isinstance(cfg.get("club"), dict) and not cfg["club"].get("name"):
        errors.append("club.name обязателен")
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/reset")
def setup_reset(
    payload: ResetRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "owner")),
):
    """E30.15 — сброс настроек мастера"""
    if not payload.confirmation:
        raise HTTPException(status_code=400, detail="Требуется подтверждение")
    db.execute(text("DELETE FROM setup_wizard"))
    db.commit()
    try:
        if SETUP_STATE_PATH.exists():
            SETUP_STATE_PATH.unlink()
    except Exception:
        pass
    return {"message": "Настройки сброшены", "setup_required": True}
