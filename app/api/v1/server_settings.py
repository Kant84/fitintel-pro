"""Волна 5: серверные настройки сторонних сервисов — в БД, редактируются из десктопа
(«Настройки → Сервисы»), а не через ssh/.env. Сервисы читают: env <- server_settings (переопределяет).
GET — маскированные значения (видно только «задано/не задано»), PUT — запись (admin/owner)."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text as _t
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db, engine

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
    "BANK_CONFIG": "Банк-эквайринг: JSON конфиг (см. docs)",
}
KEY_RE = re.compile(r"^[A-Z0-9_]{2,60}$")
SECRETISH = ("KEY", "PASSWORD", "SECRET", "TOKEN")


def _ensure():
    with engine.begin() as c:
        c.execute(_t("CREATE TABLE IF NOT EXISTS server_settings("
                     "key VARCHAR(60) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"))


def get_map() -> dict:
    """Все настройки (сырые) — для сервисов."""
    try:
        _ensure()
        with engine.begin() as c:
            rows = c.execute(_t("SELECT key, value FROM server_settings")).fetchall()
        return {k: v for k, v in rows if v not in (None, "")}
    except Exception:
        return {}


class SettingIn(BaseModel):
    key: str
    value: str


@router.get("/server-settings")
def list_settings(user=Depends(get_current_user)):
    _ensure()
    m = get_map()
    out = []
    for k, descr in KNOWN_KEYS.items():
        v = m.get(k)
        if v is None:
            shown, set_ = None, False
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
    _ensure()
    with engine.begin() as c:
        c.execute(_t("INSERT INTO server_settings(key, value, updated_at) VALUES(:k,:v,NOW()) "
                     "ON CONFLICT(key) DO UPDATE SET value=:v, updated_at=NOW()"),
                   {"k": body.key, "v": body.value})
    return {"ok": True, "key": body.key}