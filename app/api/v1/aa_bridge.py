"""E21: Интеграция с A&A — импорт/экспорт + webhook."""
from __future__ import annotations
import io, csv
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.api.v1.license_api import _eng

router = APIRouter()

def _ensure():
    try:
        with _eng().begin() as c:
            c.execute(text("""CREATE TABLE IF NOT EXISTS aa_sync_log (
                id SERIAL PRIMARY KEY, direction VARCHAR(10), entity VARCHAR(20),
                records_count INTEGER, status VARCHAR(20), detail TEXT,
                created_at TIMESTAMP DEFAULT NOW())"""))
    except Exception as e:
        print("[E21] ensure:", e)

_ensure()

class AASyncIn(BaseModel):
    clients: list = []

class CSVImportIn(BaseModel):
    csv: str
    entity: str = "clients"

def _log(direction, entity, count, status, detail=""):
    try:
        with _eng().begin() as c:
            c.execute(text("""INSERT INTO aa_sync_log (direction, entity, records_count, status, detail)
                VALUES (:d, :e, :c, :s, :dt)"""),
                {"d": direction, "e": entity, "c": count, "s": status, "dt": detail})
    except Exception:
        pass

CLIENT_MAP = {
    "fio": ["фио", "fio", "fullname", "полное имя", "клиент"],
    "first_name": ["имя", "first_name", "name", "имя клиента"],
    "last_name": ["фамилия", "last_name", "surname", "фамилия клиента"],
    "middle_name": ["отчество", "middle_name", "patronymic"],
    "phone": ["телефон", "phone", "тел", "mobile", "телефон клиента"],
    "email": ["email", "почта", "e-mail", "mail", "электронная почта"],
    "birth_date": ["дата рождения", "birthday", "birth_date", "др"],
    "gender": ["пол", "gender", "sex"],
    "client_category": ["категория", "category", "client_category", "тип клиента"],
    "status": ["статус", "status", "состояние"],
    "photo_url": ["фото", "photo", "photo_url", "url фото", "изображение"],
}

def _detect_cols(headers, mapping):
    result = {}
    headers_lower = [h.lower().strip() for h in headers]
    for std, variants in mapping.items():
        for v in variants:
            if v in headers_lower:
                result[std] = headers_lower.index(v)
                break
    return result

def _parse_fio(fio):
    parts = str(fio).strip().split() if fio else []
    return {
        "last_name": parts[0] if len(parts) > 0 else "",
        "first_name": parts[1] if len(parts) > 1 else "",
        "middle_name": parts[2] if len(parts) > 2 else ""
    }

def _norm_gender(v):
    v = str(v).lower().strip() if v else ""
    if v in ("м", "муж", "мужской", "male", "m"): return "MALE"
    if v in ("ж", "жен", "женский", "female", "f"): return "FEMALE"
    return "НЕ_УКАЗАН"

def _norm_category(v):
    v = str(v).lower().strip() if v else ""
    if v in ("vip", "вип"): return "VIP"
    if v in ("child", "ребенок", "детский"): return "CHILD"
    if v in ("пенсионер", "pensioner"): return "ПЕНСИОНЕР"
    if v in ("инвалид", "disabled"): return "ИНВАЛИД"
    if v in ("корпоративный", "corporate"): return "КОРПОРАТИВНЫЙ"
    if v in ("staff", "сотрудник"): return "STAFF"
    return "ADULT"

def _norm_status(v):
    v = str(v).lower().strip() if v else ""
    if v in ("active", "активный", "активен", "ok", "trial", "пробный"): return "ACTIVE"
    if v in ("blocked", "заблокирован", "блок"): return "BLOCKED"
    return "INACTIVE"

def _import_client(data):
    with _eng().begin() as c:
        c.execute(text("""INSERT INTO clients (id, first_name, last_name, middle_name, phone, email, birth_date, gender, client_category, status, photo_url, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), :fn, :ln, :mn, :p, :e, :b, :g, :cc, :st, :ph, true, NOW(), NOW())
            ON CONFLICT (phone) DO UPDATE SET
                first_name=COALESCE(EXCLUDED.first_name, clients.first_name),
                last_name=COALESCE(EXCLUDED.last_name, clients.last_name),
                middle_name=COALESCE(EXCLUDED.middle_name, clients.middle_name),
                email=COALESCE(EXCLUDED.email, clients.email),
                birth_date=COALESCE(EXCLUDED.birth_date, clients.birth_date),
                gender=COALESCE(EXCLUDED.gender, clients.gender),
                photo_url=COALESCE(EXCLUDED.photo_url, clients.photo_url),
                client_category=COALESCE(EXCLUDED.client_category, clients.client_category),
                status=COALESCE(EXCLUDED.status, clients.status),
                updated_at=NOW()"""),
            {"fn": data.get("first_name", ""), "ln": data.get("last_name", ""), "mn": data.get("middle_name"),
             "p": data.get("phone", ""), "e": data.get("email"), "b": data.get("birth_date") or None,
             "g": _norm_gender(data.get("gender")), "cc": _norm_category(data.get("client_category")), "st": _norm_status(data.get("status")), "ph": data.get("photo_url") or None})

@router.post("/aa/import-csv")
def import_aa_csv(payload: CSVImportIn):
    """Импорт CSV из A&A."""
    if payload.entity not in ("clients",):
        raise HTTPException(400, "entity: clients")
    reader = csv.reader(io.StringIO(payload.csv), delimiter=";")
    headers = next(reader, [])
    cols = _detect_cols(headers, CLIENT_MAP)
    if not cols:
        raise HTTPException(400, f"Не распознаны колонки. Заголовки: {headers}")
    imported = 0
    errors = []
    for i, row in enumerate(reader, 2):
        if not row:
            continue
        try:
            data = {k: (row[idx] if idx < len(row) else "") for k, idx in cols.items()}
            # Если ФИО в одной колонке — парсим
            if "fio" in cols or "fullname" in cols:
                fio_key = "fio" if "fio" in cols else "fullname"
                parsed = _parse_fio(data.get(fio_key, ""))
                data.update(parsed)
            _import_client(data)
            imported += 1
        except Exception as e:
            errors.append(f"строка {i}: {str(e)[:80]}")
    _log("import", payload.entity, imported, "ok" if not errors else "partial", "; ".join(errors[:5]))
    return {"imported": imported, "errors": len(errors), "details": errors[:10]}

@router.post("/aa/webhook")
def aa_webhook(payload: AASyncIn):
    total = 0
    for item in payload.clients:
        try:
            _import_client(item)
            total += 1
        except Exception as e:
            print(f"[E21] webhook:", str(e)[:80])
    _log("webhook", "clients", total, "ok")
    return {"processed": total}

@router.get("/aa/export")
def export_aa(entity: str = "clients", format: str = "json"):
    if entity == "clients":
        with _eng().begin() as c:
            rows = c.execute(text("""
                SELECT first_name, last_name, middle_name, phone, email, birth_date, gender, client_category, status, is_active, created_at 
                FROM clients ORDER BY created_at DESC LIMIT 1000
            """)).mappings().all()
        out = [dict(r) for r in rows]
    else:
        raise HTTPException(400, "entity: clients")
    _log("export", entity, len(out), "ok")
    if format == "csv":
        buf = io.StringIO()
        if out:
            import csv as _csv
            w = _csv.DictWriter(buf, fieldnames=list(out[0].keys()), delimiter=";")
            w.writeheader()
            for r in out:
                w.writerow({k: str(v) if v is not None else "" for k, v in r.items()})
        return {"csv": "\ufeff" + buf.getvalue()}
    return {"data": out, "count": len(out)}

@router.get("/aa/sync-log")
def sync_log(limit: int = 50):
    with _eng().begin() as c:
        rows = c.execute(text("SELECT * FROM aa_sync_log ORDER BY id DESC LIMIT :l"), {"l": limit}).mappings().all()
    return [dict(r) for r in rows]
