"""Волна 5: параметры клуба (время/окна) и лейблы бота — хранятся на сервере,
редактируются из десктопа. Паттерны как в messenger.py/branding.py (raw-SQL).
"""
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db

router = APIRouter(tags=["club-params"])

engine = None
for mod in ("app.db.session", "app.core.database", "app.database"):
    try:
        m = __import__(mod, fromlist=["engine"])
        engine = m.engine
        break
    except Exception:
        continue
if engine is None:
    raise RuntimeError("club_params: engine not found")

DEFAULT_PARAMS = {
    "SLOT_MINUTES": ("45", "Длительность слота тренера, минут"),
    "CONFIRM_DEADLINE_HOURS": ("6", "Дедлайн подтверждения брони до занятия, часов"),
    "REMIND_BEFORE_HOURS": ("24", "Напоминание + запрос подтверждения, часов до занятия"),
    "LAST_REMIND_BEFORE_HOURS": ("2", "Финальный пин «подтвердите», часов до занятия"),
    "QR_ACCESS_WINDOW_HOURS": ("1", "Окно входа по QR вокруг занятия, часов (±)"),
    "QR_TTL_MINUTES": ("2", "Время жизни QR, минут"),
    "QR_REFRESH_COOLDOWN_SECONDS": ("20", "Пауза между обновлениями QR в боте, секунд"),
    "CANCEL_WINDOW_HOURS": ("24", "Бесплатная отмена записи не позднее, часов"),
    "ONLINE_BOOKING_ENABLED": ("true", "Онлайн-запись из MAX: true/false"),
}

DEFAULT_LABELS = {
    "TXT.MENU.SHOP": "🛍 Магазин",
    "TXT.MENU.SCHEDULE": "🗓 Расписание занятий",
    "TXT.MENU.TRAINER": "👤 Личный тренер",
    "TXT.MENU.BONUSES": "🎁 Бонусы",
    "TXT.MENU.MY": "📋 Мои записи",
    "TXT.MENU.QR": "🔳 QR на вход",
    "TXT.QR.TITLE": "✅ Основание для входа",
    "TXT.QR.NO_ACCESS": ("Вход по QR доступен при активном абонементе или оплаченном занятии. "
                         "Купить можно в разделе «Магазин» или на ресепшене."),
    "TXT.BONUSES.SOON": "Программа бонусов скоро появится!",
    "TXT.CONFIRM.OK": "✅ Запись подтверждена. Ждём вас!",
    "TXT.CANCEL.OK": "❌ Запись отменена. Слот освобождён.",
    "TXT.SCHEDULE.EMPTY": "Сегодня групповых занятий нет.",
    "TXT.TRAINER.EMPTY": "Свободных окон нет — уточните на ресепшене.",
}

_cache = {"ts": 0.0, "params": None, "labels": None}
CACHE_TTL = 60.0


def _ensure():
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS club_params("
                       "key TEXT PRIMARY KEY, value TEXT NOT NULL, description TEXT)"))
        if engine.dialect.name == "postgresql":
            cols = {r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='clients'"))}
            if "rating" not in cols:
                c.execute(text("ALTER TABLE clients ADD COLUMN rating DOUBLE PRECISION DEFAULT 5.0"))
            t = {r[0] for r in c.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_name='branding_settings'"))}
            if "branding_settings" in t:
                bcols = {r[0] for r in c.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='branding_settings'"))}
                if "bot_labels" not in bcols:
                    c.execute(text("ALTER TABLE branding_settings ADD COLUMN bot_labels TEXT"))
        else:
            cols = {r[1] for r in c.execute(text("PRAGMA table_info(clients)"))}
            if "rating" not in cols:
                c.execute(text("ALTER TABLE clients ADD COLUMN rating FLOAT DEFAULT 5.0"))


def _load_params() -> dict:
    with engine.begin() as c:
        rows = c.execute(text("SELECT key, value FROM club_params")).fetchall()
    data = {k: d[0] for k, d in DEFAULT_PARAMS.items()}
    data.update({r[0]: r[1] for r in rows if not r[0].startswith("LBL:")})
    return data


def _load_labels() -> dict:
    data = dict(DEFAULT_LABELS)
    try:
        with engine.begin() as c:
            row = c.execute(text("SELECT bot_labels FROM branding_settings WHERE id=1")).fetchone()
        if row and row[0]:
            data.update(json.loads(row[0]))
    except Exception:
        pass
    try:  # фолбэк/override: LBL:* в club_params
        with engine.begin() as c:
            rows = c.execute(text("SELECT key, value FROM club_params WHERE key LIKE 'LBL:%'")).fetchall()
        for k, v in rows:
            data[k[4:]] = v
    except Exception:
        pass
    return data


def _reload(force: bool = False):
    now = time.time()
    if not force and _cache["params"] is not None and now - _cache["ts"] < CACHE_TTL:
        return
    try:
        _ensure()
    except Exception:
        pass
    _cache.update(ts=now, params=_load_params(), labels=_load_labels())


def get_param(key: str, default: Optional[str] = None) -> Optional[str]:
    _reload()
    v = _cache["params"].get(key, default)
    return default if v is None else v


def get_param_int(key: str, default: int) -> int:
    try:
        return int(get_param(key, str(default)))
    except (TypeError, ValueError):
        return default


def get_label(key: str, default: str = "") -> str:
    _reload()
    return str(_cache["labels"].get(key, default))


class ParamIn(BaseModel):
    value: str


class LabelIn(BaseModel):
    value: str


@router.get("/club-params")
def list_params(user=Depends(get_current_user)):
    _reload(force=True)
    return [{"key": k, "value": v,
             "description": DEFAULT_PARAMS.get(k, ("", "Переопределение клуба"))[1]}
            for k, v in sorted(_cache["params"].items())]


@router.put("/club-params/{key}")
def put_param(key: str, body: ParamIn, db: Session = Depends(get_db),
              user=Depends(require_permission("settings.update"))):
    if key not in DEFAULT_PARAMS:
        raise HTTPException(status_code=404, detail="Неизвестный параметр")
    _ensure()
    with engine.begin() as c:
        c.execute(text("INSERT INTO club_params(key, value, description) VALUES(:k,:v,:d) "
                       "ON CONFLICT(key) DO UPDATE SET value=:v"),
                  {"k": key, "v": str(body.value), "d": DEFAULT_PARAMS[key][1]})
    _reload(force=True)
    return {"ok": True, "key": key, "value": body.value}


@router.get("/bot-labels")
def list_labels(user=Depends(get_current_user)):
    _reload(force=True)
    return {"labels": _cache["labels"], "defaults": DEFAULT_LABELS}


@router.put("/bot-labels/{key}")
def put_label(key: str, body: LabelIn, db: Session = Depends(get_db),
              user=Depends(require_permission("settings.update"))):
    if not key or len(key) > 60 or " " in key:
        raise HTTPException(status_code=422, detail="Ключ лейбла: до 60 символов, без пробелов")
    _ensure()
    saved = False
    try:  # предпочтительно — в branding_settings.bot_labels
        with engine.begin() as c:
            row = c.execute(text("SELECT bot_labels FROM branding_settings WHERE id=1")).fetchone()
            cur = json.loads(row[0]) if row and row[0] else {}
            cur[key] = body.value
            c.execute(text("UPDATE branding_settings SET bot_labels=:b WHERE id=1"),
                      {"b": json.dumps(cur, ensure_ascii=False)})
        saved = True
    except Exception:
        pass
    if not saved:  # фолбэк — в club_params с префиксом LBL:
        with engine.begin() as c:
            c.execute(text("INSERT INTO club_params(key, value, description) VALUES(:k,:v,:d) "
                           "ON CONFLICT(key) DO UPDATE SET value=:v"),
                      {"k": "LBL:" + key, "v": body.value, "d": "Лейбл бота"})
    _reload(force=True)
    return {"ok": True, "key": key, "value": body.value}