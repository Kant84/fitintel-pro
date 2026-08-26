"""E19: Экспорт данных (xlsx/json, JWT-ссылки) + 152-ФЗ право на забвение."""
from __future__ import annotations
import io, json, urllib.request
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from app.api.v1.license_api import _eng

router = APIRouter()

ALLOWED = {
    "clients": "clients", "payments": "payments", "visits": "visits",
    "subscriptions": "subscriptions", "tariffs": "tariffs", "users": "users",
    "tenants": "tenants", "notification_log": "notification_log",
}
SECRET_KEYS = ("pass", "hash", "secret", "token")

def _valid_token(token: str) -> bool:
    if not token:
        return False
    try:
        req = urllib.request.Request("http://localhost:8001/api/v1/ui-config/my")
        req.add_header("Authorization", "Bearer " + token)
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False

def _ensure():
    try:
        with _eng().begin() as c:
            c.execute(text("""CREATE TABLE IF NOT EXISTS export_log (
                id SERIAL PRIMARY KEY,
                action TEXT, entity TEXT, fmt TEXT,
                detail TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW())"""))
    except Exception as e:
        print("[E19] ensure:", e)

_ensure()

def _log(action, entity, fmt="", detail=""):
    try:
        with _eng().begin() as c:
            c.execute(text("INSERT INTO export_log (action, entity, fmt, detail) VALUES (:a,:e,:f,:d)"),
                      {"a": action, "e": entity, "f": fmt, "d": detail})
    except Exception:
        pass

def _rows(table):
    with _eng().begin() as c:
        rows = c.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
    out = []
    for r in rows:
        d = {}
        for k, v in dict(r).items():
            if any(s in k.lower() for s in SECRET_KEYS):
                d[k] = "***"
            elif isinstance(v, Decimal):
                d[k] = float(v)
            elif isinstance(v, (datetime, date)):
                d[k] = v.isoformat()
            else:
                d[k] = v if isinstance(v, (int, float, str, bool)) or v is None else str(v)
        out.append(d)
    return out

@router.get("/export/log/list")
def export_log(limit: int = 50, token: str = Query("")):
    if not _valid_token(token):
        raise HTTPException(401, "Некорректный токен")
    with _eng().begin() as c:
        rows = c.execute(text("SELECT * FROM export_log ORDER BY id DESC LIMIT :l"), {"l": limit}).mappings().all()
    return [dict(r) for r in rows]

@router.get("/export/{entity}")
def export_entity(entity: str, fmt: str = Query("json"), token: str = Query("")):
    if entity not in ALLOWED:
        raise HTTPException(404, "Неизвестная сущность. Доступно: " + ", ".join(sorted(ALLOWED)))
    if not _valid_token(token):
        raise HTTPException(401, "Некорректный токен")
    try:
        rows = _rows(ALLOWED[entity])
    except Exception as e:
        raise HTTPException(404, f"Таблица '{ALLOWED[entity]}' недоступна: {str(e)[:150]}")
    _log("export", entity, fmt)
    if fmt == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError:
            raise HTTPException(500, "openpyxl не установлен на сервере")
        wb = Workbook()
        ws = wb.active
        ws.title = entity
        cols = list(rows[0].keys()) if rows else ["info"]
        ws.append(cols)
        for r in rows:
            ws.append([r.get(c) for c in cols])
        if not rows:
            ws.append(["нет данных"])
        buf = io.BytesIO()
        wb.save(buf)
        return Response(buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={entity}.xlsx"})
    if fmt == "csv":
        import csv as _csv
        buf2 = io.StringIO()
        w = _csv.writer(buf2, delimiter=";")
        cols = list(rows[0].keys()) if rows else ["info"]
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])
        return Response(("\ufeff" + buf2.getvalue()).encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={entity}.csv"})
    return Response(json.dumps(rows, ensure_ascii=False, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={entity}.json"})

class ForgetIn(BaseModel):
    client_id: str
    reason: str = "запрос субъекта (152-ФЗ)"

ANON_FIELDS = ["name", "first_name", "last_name", "middle_name", "full_name", "fio",
               "phone", "email", "birth_date", "birthday", "address", "comment", "notes"]

@router.post("/export/forget")
def forget_client(p: ForgetIn, token: str = Query("")):
    if not _valid_token(token):
        raise HTTPException(401, "Некорректный токен")
    eng = _eng()
    with eng.begin() as c:
        cols = {r[0] for r in c.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='clients'"))}
    parts, params = [], {"id": p.client_id}
    found = []
    for f in ANON_FIELDS:
        if f in cols:
            found.append(f)
            if f in ("birth_date", "birthday"):
                parts.append(f'"{f}"=NULL')
            else:
                parts.append(f'"{f}"=:v_{f}')
                params[f"v_{f}"] = "***"
    if not parts:
        raise HTTPException(500, "Не найдены персональные поля в clients")
    with eng.begin() as c:
        res = c.execute(text(f'UPDATE clients SET {", ".join(parts)} WHERE "id"::text=:id'), params)
    if res.rowcount == 0:
        raise HTTPException(404, "Клиент не найден")
    _log("forget", "clients", "", f"client_id={p.client_id}; {p.reason}")
    return {"ok": True, "anonymized": found}

@router.get("/export")
def export_index():
    return {"entities": sorted(ALLOWED), "formats": ["json", "xlsx", "csv"], "auth": "?token=JWT"}
