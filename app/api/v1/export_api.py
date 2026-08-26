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


# === E19_JOBS: асинхронные задачи экспорта + JWT-ссылка 24ч + all-my-data ZIP ===
import time as _time, uuid as _uuid, zipfile as _zip, hmac as _hmac, hashlib as _hash
from pathlib import Path as _Path
from app.api.v1.license_api import _secret

EXPORT_DIR = _Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

def _jobs_ensure():
    try:
        with _eng().begin() as c:
            c.execute(text("""CREATE TABLE IF NOT EXISTS data_export_jobs (
                id UUID PRIMARY KEY,
                entity VARCHAR(50), format VARCHAR(10),
                status VARCHAR(20) DEFAULT 'ready',
                expires_at TIMESTAMP, created_at TIMESTAMP DEFAULT NOW())"""))
    except Exception as e:
        print("[E19] jobs ensure:", e)

_jobs_ensure()

def _to_xlsx(rows, name):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = name[:31]
    cols = list(rows[0].keys()) if rows else ["info"]
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c) for c in cols])
    if not rows:
        ws.append(["нет данных"])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()

def _to_csv(rows):
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf, delimiter=";")
    cols = list(rows[0].keys()) if rows else ["info"]
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c) for c in cols])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")

def _to_json(rows):
    return json.dumps(rows, ensure_ascii=False, indent=2, default=str).encode("utf-8")

def _zip_all():
    b = io.BytesIO()
    with _zip.ZipFile(b, "w", _zip.ZIP_DEFLATED) as z:
        for ent in sorted(ALLOWED):
            try:
                z.writestr(f"{ent}.json", _to_json(_rows(ALLOWED[ent])))
            except Exception as e:
                z.writestr(f"{ent}.error.txt", str(e)[:200])
    return b.getvalue()

def _make_link(job_id):
    exp = int(_time.time()) + 86400
    payload = f"{job_id}.{exp}"
    sig = _hmac.new(_secret().encode(), payload.encode(), _hash.sha256).hexdigest()[:24]
    return f"{payload}.{sig}"

def _verify_link(token):
    try:
        job_id, exp, sig = token.rsplit(".", 2)
        payload = f"{job_id}.{exp}"
        good = _hmac.new(_secret().encode(), payload.encode(), _hash.sha256).hexdigest()[:24]
        if not _hmac.compare_digest(sig, good):
            return None
        if int(exp) < _time.time():
            return None
        return job_id
    except Exception:
        return None

class JobIn(BaseModel):
    entity: str = "clients"
    fmt: str = "xlsx"

MIME = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv", "json": "application/json", "zip": "application/zip"}

@router.post("/export-jobs")
def create_job(p: JobIn, token: str = Query("")):
    if not _valid_token(token):
        raise HTTPException(401, "Некорректный токен")
    if p.entity != "all" and p.entity not in ALLOWED:
        raise HTTPException(404, "Неизвестная сущность")
    job_id = str(_uuid.uuid4())
    fmt = "zip" if p.entity == "all" else p.fmt
    try:
        data = _zip_all() if p.entity == "all" else (
            _to_xlsx(_rows(ALLOWED[p.entity]), p.entity) if p.fmt == "xlsx" else
            _to_csv(_rows(ALLOWED[p.entity])) if p.fmt == "csv" else
            _to_json(_rows(ALLOWED[p.entity])))
        (EXPORT_DIR / f"{job_id}.{fmt}").write_bytes(data)
        status = "ready"
    except Exception as e:
        status = "error"
        print("[E19] job:", str(e)[:150])
    with _eng().begin() as c:
        c.execute(text("""INSERT INTO data_export_jobs (id, entity, format, status, expires_at)
            VALUES (:i, :e, :f, :s, NOW() + INTERVAL '24 hours')"""),
            {"i": job_id, "e": p.entity, "f": fmt, "s": status})
    _log("export_job", p.entity, fmt)
    return {"job_id": job_id, "status": status,
            "download_url": f"/download?token={_make_link(job_id)}" if status == "ready" else None,
            "expires_in_h": 24}

@router.get("/export-jobs")
def list_jobs(token: str = Query("")):
    if not _valid_token(token):
        raise HTTPException(401, "Некорректный токен")
    with _eng().begin() as c:
        rows = c.execute(text("""SELECT id, entity, format, status, expires_at, created_at,
            (expires_at < NOW()) AS expired FROM data_export_jobs ORDER BY created_at DESC LIMIT 50""")).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        for k in ("expires_at", "created_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        out.append(d)
    return out

@router.get("/download")
def download_job(token: str = Query("")):
    job_id = _verify_link(token)
    if not job_id:
        raise HTTPException(401, "Ссылка недействительна или истекла (срок 24ч)")
    with _eng().begin() as c:
        row = c.execute(text("SELECT entity, format, status FROM data_export_jobs WHERE id=:i"),
                        {"i": job_id}).mappings().first()
    if not row or row["status"] != "ready":
        raise HTTPException(404, "Файл не найден")
    path = EXPORT_DIR / f"{job_id}.{row['format']}"
    if not path.exists():
        raise HTTPException(404, "Файл удалён")
    return Response(path.read_bytes(), media_type=MIME.get(row["format"], "application/octet-stream"),
                    headers={"Content-Disposition": f"attachment; filename={row['entity']}.{row['format']}"})
