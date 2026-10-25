"""Серверные настройки внешних сервисов и безопасный редактор банков."""
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text as _t
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_current_user, require_roles
from app.api.v1.ui_config import _user_role, ensure_bank_screen
from app.db.session import get_db, engine
from app.services.audit_service import AuditService

router = APIRouter(tags=["server-settings"])

KNOWN_KEYS = {
    "YOOKASSA_ACCOUNT_ID": "ЮKassa: идентификатор магазина",
    "YOOKASSA_SECRET_KEY": "ЮKassa: секретный ключ",
    "YOOKASSA_WEBHOOK_SECRET": "ЮKassa: секрет webhook",
    "YOOKASSA_TEST_MODE": "ЮKassa: тестовый режим (true/false)",
    "MAX_BOT_TOKEN": "MAX: токен бота",
    "MAX_BOT_WEBHOOK_SECRET": "MAX: секрет webhook (опционально)",
    "TELEGRAM_BOT_TOKEN": "Telegram: токен бота",
    "SMS_USER": "SMS (smsc.ru): логин",
    "SMS_PASSWORD": "SMS (smsc.ru): пароль",
    "ITC_BASIC_USER": "СКУД ITC: пользователь Basic Auth",
    "ITC_BASIC_PASSWORD": "СКУД ITC: пароль",
    "SBP_MOCK": "СБП: тестовый режим (true/false)",
    "BANK_CONFIG": "Банки: редактируются в разделе «Банки»",
}
KEY_RE = re.compile(r"^[A-Z0-9_]{2,60}$")
SECRETISH = ("KEY", "PASSWORD", "SECRET", "TOKEN")

BANK_FIELDS = {
    "tinkoff": {
        "terminal_key": False,
        "password": True,
        "notification_url": False,
    },
    "sber": {
        "mode": False,
        "merchant_id": False,
        "token": True,
        "callback_token": True,
        "return_url": False,
    },
    "vtb": {
        "merchant_id": False,
        "terminal_id": False,
        "api_key": True,
        "callback_token": True,
        "notification_url": False,
        "return_url": False,
    },
    "alfa": {
        "merchant_id": False,
        "terminal_id": False,
        "api_key": True,
        "callback_token": True,
        "notification_url": False,
        "return_url": False,
    },
    "psb": {
        "merchant_id": False,
        "terminal_id": False,
        "api_key": True,
        "callback_token": True,
        "notification_url": False,
        "return_url": False,
    },
}
SUPPORTED_BANKS = {"tinkoff", "sber"}
REQUIRED_ACTIVE_FIELDS = {
    "tinkoff": ("terminal_key", "password", "notification_url"),
    "sber": ("mode", "merchant_id", "token", "callback_token", "return_url"),
}


def _ensure():
    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS server_settings("
            "key VARCHAR(60) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"
        ))


def get_map() -> dict:
    """Сырые настройки только для внутренних сервисов, не для API-ответов."""
    try:
        _ensure()
        with engine.begin() as c:
            rows = c.execute(_t("SELECT key, value FROM server_settings")).fetchall()
        return {k: v for k, v in rows if v not in (None, "")}
    except Exception:
        return {}


def _bank_config() -> dict:
    raw = get_map().get("BANK_CONFIG", "")
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _save_bank_config(config: dict) -> None:
    value = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    _ensure()
    with engine.begin() as c:
        c.execute(_t(
            "INSERT INTO server_settings(key, value, updated_at) "
            "VALUES('BANK_CONFIG', :value, NOW()) "
            "ON CONFLICT(key) DO UPDATE SET value=:value, updated_at=NOW()"
        ), {"value": value})


def _require_bank_screen(user, db: Session):
    """Доступ определяется той же матрицей, что показывает экран «Банки»."""
    if getattr(user, "is_superuser", False) or str(
            getattr(user, "username", "")).lower() == "superadmin":
        return user
    ensure_bank_screen(db)
    role = _user_role(user)
    allowed = db.execute(_t(
        "SELECT 1 FROM ui_role_screens rs "
        "JOIN ui_screens s ON s.code=rs.screen_code "
        "WHERE rs.role=:role AND rs.screen_code='banks' "
        "AND rs.is_visible AND s.is_active"
    ), {"role": role}).first()
    if not allowed:
        raise HTTPException(403, "Экран «Банки» не разрешён для вашей роли")
    return user


class SettingIn(BaseModel):
    key: str
    value: str


class BankConfigIn(BaseModel):
    active: str = ""
    providers: dict[str, dict[str, Optional[str]]] = {}


@router.get("/server-settings")
def list_settings(user=Depends(get_current_user)):
    _ensure()
    m = get_map()
    out = []
    for k, descr in KNOWN_KEYS.items():
        v = m.get(k)
        if v is None:
            shown, set_ = None, False
        elif k == "BANK_CONFIG":
            shown, set_ = "••••••", True
        elif any(s in k for s in SECRETISH) and k != "SBP_MOCK":
            shown, set_ = "•" * 6 + str(v)[-4:], True
        else:
            shown, set_ = str(v)[:60], True
        out.append({"key": k, "value": shown, "is_set": set_, "description": descr})
    return out


@router.put("/server-settings")
def put_setting(body: SettingIn, db: Session = Depends(get_db),
                user=Depends(require_roles("admin", "owner"))):
    if not KEY_RE.match(body.key):
        raise HTTPException(422, "Ключ: заглавные буквы/цифры/подчёркивание")
    if body.key == "BANK_CONFIG":
        raise HTTPException(400, "BANK_CONFIG изменяется только в разделе «Банки»")
    _ensure()
    with engine.begin() as c:
        c.execute(_t(
            "INSERT INTO server_settings(key, value, updated_at) VALUES(:k,:v,NOW()) "
            "ON CONFLICT(key) DO UPDATE SET value=:v, updated_at=NOW()"
        ), {"k": body.key, "v": body.value})
    return {"ok": True, "key": body.key}


@router.get("/server-settings/bank-config")
def get_bank_settings(db: Session = Depends(get_db),
                      user=Depends(get_current_active_user)):
    _require_bank_screen(user, db)
    config = _bank_config()
    providers = {}
    for provider, fields in BANK_FIELDS.items():
        saved = config.get(provider) if isinstance(config.get(provider), dict) else {}
        providers[provider] = {
            "supported": provider in SUPPORTED_BANKS,
            "fields": {
                key: {
                    "secret": secret,
                    "is_set": bool(saved.get(key)),
                    "value": "" if secret else str(saved.get(key) or ""),
                }
                for key, secret in fields.items()
            },
        }
    return {"active": str(config.get("active") or ""), "providers": providers}


@router.put("/server-settings/bank-config")
def put_bank_settings(body: BankConfigIn, db: Session = Depends(get_db),
                      user=Depends(get_current_active_user)):
    _require_bank_screen(user, db)
    active = body.active.strip().lower()
    if active and active not in SUPPORTED_BANKS:
        raise HTTPException(422, "Приём платежей пока поддерживается только для Т-Банка и Сбера")
    unknown_providers = set(body.providers) - set(BANK_FIELDS)
    if unknown_providers:
        raise HTTPException(422, "Неизвестный банк: " + ", ".join(sorted(unknown_providers)))

    config = _bank_config()
    changed = []
    for provider, incoming in body.providers.items():
        allowed = BANK_FIELDS[provider]
        unknown_fields = set(incoming) - set(allowed)
        if unknown_fields:
            raise HTTPException(422, f"{provider}: неизвестные поля: " + ", ".join(sorted(unknown_fields)))
        saved = config.setdefault(provider, {})
        if not isinstance(saved, dict):
            saved = {}
            config[provider] = saved
        for key, value in incoming.items():
            secret = allowed[key]
            if secret and value == "":
                continue  # пустое секретное поле = не менять сохранённый секрет
            if value is None:
                if secret:
                    saved.pop(key, None)
                    changed.append(f"{provider}.{key}:cleared")
                else:
                    saved[key] = ""
                continue
            value = value.strip()
            if len(value) > 4000:
                raise HTTPException(422, f"{provider}.{key}: значение длиннее 4000 символов")
            if key.endswith("_url") and value and not value.startswith("https://"):
                raise HTTPException(422, f"{provider}.{key}: нужен публичный HTTPS URL")
            saved[key] = value
            changed.append(f"{provider}.{key}")

    config["active"] = active
    if active:
        options = config.get(active) or {}
        missing = [key for key in REQUIRED_ACTIVE_FIELDS[active] if not options.get(key)]
        if missing:
            raise HTTPException(422, f"Для активации заполните: {', '.join(missing)}")
        if active == "sber" and options.get("mode") != "json":
            raise HTTPException(422, "Для Сбера поддерживается mode=json")

    _save_bank_config(config)
    AuditService(db).log(
        action="bank_settings.update",
        status="success",
        actor_user_id=user.id,
        entity_type="server_setting",
        after_data={"active": active, "changed_fields": changed},
    )
    db.commit()
    return {"ok": True, "active": active}
