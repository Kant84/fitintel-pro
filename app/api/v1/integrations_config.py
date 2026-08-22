# -*- coding: utf-8 -*-
"""E56: настройки интеграций (API-ключи 1С, Mobifitness, MAX, ЮKassa)."""
import json
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

engine = None
for mod in ("app.db.session", "app.core.database", "app.database"):
    try:
        m = __import__(mod, fromlist=["engine"])
        engine = getattr(m, "engine")
        break
    except Exception:
        continue
if engine is None:
    raise RuntimeError("integrations_config: engine not found")

router = APIRouter(tags=["integrations-config"])

SERVICES = {
    "1c": {"title": "1С (бухгалтерия)", "fields": [
        {"key": "api_url", "label": "URL API 1С"},
        {"key": "login", "label": "Логин"},
        {"key": "password", "label": "Пароль", "secret": True},
        {"key": "enabled", "label": "Включено (true/false)"}]},
    "mobifitness": {"title": "Mobifitness", "fields": [
        {"key": "api_url", "label": "URL API"},
        {"key": "api_key", "label": "API-ключ", "secret": True},
        {"key": "club_id", "label": "ID клуба"},
        {"key": "enabled", "label": "Включено (true/false)"}]},
    "max_messenger": {"title": "MAX (мессенджер)", "fields": [
        {"key": "bot_token", "label": "Токен бота MAX", "secret": True},
        {"key": "support_chat", "label": "Чат поддержки (URL)"},
        {"key": "enabled", "label": "Включено (true/false)"}]},
    "yookassa": {"title": "ЮKassa", "fields": [
        {"key": "shop_id", "label": "Shop ID"},
        {"key": "secret_key", "label": "Секретный ключ", "secret": True},
        {"key": "enabled", "label": "Включено (true/false)"}]},
}


def _ensure():
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS integration_settings("
            "service TEXT PRIMARY KEY, config TEXT, updated_at TEXT)"))


def _load(service):
    _ensure()
    with engine.begin() as c:
        row = c.execute(text(
            "SELECT config, updated_at FROM integration_settings WHERE service=:s"),
            {"s": service}).fetchone()
    return (json.loads(row[0]) if row and row[0] else {},
            row[1] if row else None)


class CfgIn(BaseModel):
    config: dict


@router.get("/integrations-config/schema")
def schema():
    return SERVICES


@router.get("/integrations-config/")
def list_all():
    out = []
    for code, meta in SERVICES.items():
        cfg, upd = _load(code)
        masked = dict(cfg)
        for f in meta["fields"]:
            if f.get("secret") and masked.get(f["key"]):
                masked[f["key"]] = "***"
        out.append({"service": code, "title": meta["title"],
                    "configured": any(str(v) for v in cfg.values()),
                    "config": masked, "updated_at": upd})
    return {"items": out}


@router.put("/integrations-config/{service}")
def save(service: str, body: CfgIn):
    if service not in SERVICES:
        raise HTTPException(404, "unknown service")
    old, _u = _load(service)
    new = dict(old)
    for k, v in body.config.items():
        if v == "***":
            continue
        new[k] = v
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO integration_settings(service, config, updated_at) "
            "VALUES(:s, :cfg, :u) "
            "ON CONFLICT(service) DO UPDATE SET config=:cfg, updated_at=:u"),
            {"s": service, "cfg": json.dumps(new, ensure_ascii=False), "u": now})
    return {"ok": True, "service": service}


@router.post("/integrations-config/{service}/test")
def test(service: str):
    if service not in SERVICES:
        raise HTTPException(404, "unknown service")
    cfg, _u = _load(service)
    import requests
    if service == "max_messenger":
        tok = cfg.get("bot_token")
        if not tok:
            return {"ok": False, "detail": "bot_token не задан"}
        try:
            r = requests.get("https://platform-api.max.ru/me",
                             headers={"Authorization": tok}, timeout=10)
            return {"ok": r.status_code == 200,
                    "detail": "HTTP %s: %s" % (r.status_code, r.text[:200])}
        except Exception as e:
            return {"ok": False, "detail": str(e)}
    url = cfg.get("api_url")
    if not url:
        return {"ok": False, "detail": "api_url не задан"}
    try:
        r = requests.get(url, timeout=10)
        return {"ok": r.status_code < 500, "detail": "HTTP %s" % r.status_code}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
