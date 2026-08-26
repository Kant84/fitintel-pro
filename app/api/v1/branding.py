"""E18: Коммерция — white-label настройки и мультитенантность."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.api.v1.license_api import _eng

router = APIRouter()

BRAND_COLS = {
    "club_name": "TEXT DEFAULT ''",
    "tagline": "TEXT DEFAULT ''",
    "logo_url": "TEXT DEFAULT ''",
    "primary_color": "TEXT DEFAULT '#E6007E'",
    "accent_color": "TEXT DEFAULT '#00BFFF'",
    "support_email": "TEXT DEFAULT ''",
    "support_phone": "TEXT DEFAULT ''",
    "custom_domain": "TEXT DEFAULT ''",
    "powered_by": "BOOLEAN DEFAULT TRUE",
}

def _ensure():
    eng = _eng()
    stmts = [
        """CREATE TABLE IF NOT EXISTS branding_settings (
            id INTEGER PRIMARY KEY,
            updated_at TIMESTAMP DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE,
            name TEXT DEFAULT '',
            plan TEXT DEFAULT 'Freemium',
            max_clients INTEGER DEFAULT 300,
            contact_email TEXT DEFAULT '',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        "INSERT INTO branding_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING",
    ]
    for st in stmts:
        try:
            with eng.begin() as c:
                c.execute(text(st))
        except Exception as e:
            print("[E18] ensure:", e)
    for col, ddl in BRAND_COLS.items():
        try:
            with eng.begin() as c:
                c.execute(text(f"ALTER TABLE branding_settings ADD COLUMN IF NOT EXISTS {col} {ddl}"))
        except Exception as e:
            print("[E18] ensure col:", col, e)

_ensure()

class BrandIn(BaseModel):
    club_name: str | None = None
    tagline: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    support_email: str | None = None
    support_phone: str | None = None
    custom_domain: str | None = None
    powered_by: bool | None = None

class TenantIn(BaseModel):
    code: str
    name: str = ""
    plan: str = "Freemium"
    max_clients: int = 300
    contact_email: str = ""

class TenantUpd(BaseModel):
    name: str | None = None
    plan: str | None = None
    max_clients: int | None = None
    contact_email: str | None = None
    active: bool | None = None

@router.get("/brand/settings")
def get_settings():
    with _eng().begin() as c:
        row = c.execute(text("SELECT * FROM branding_settings WHERE id=1")).mappings().first()
    return dict(row) if row else {}

@router.post("/brand/settings")
def set_settings(p: BrandIn):
    data = {k: v for k, v in p.model_dump().items() if v is not None}
    if data:
        sets = ", ".join(f"{k}=:{k}" for k in data)
        with _eng().begin() as c:
            c.execute(text(f"UPDATE branding_settings SET {sets}, updated_at=NOW() WHERE id=1"), data)
    return {"ok": True}

@router.get("/brand/tenants")
def list_tenants():
    with _eng().begin() as c:
        rows = c.execute(text("SELECT * FROM tenants ORDER BY id")).mappings().all()
    return [dict(r) for r in rows]

@router.post("/brand/tenants")
def create_tenant(p: TenantIn):
    try:
        with _eng().begin() as c:
            c.execute(text("INSERT INTO tenants (code,name,plan,max_clients,contact_email) VALUES (:code,:name,:plan,:mc,:em)"),
                      {"code": p.code, "name": p.name, "plan": p.plan, "mc": p.max_clients, "em": p.contact_email})
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(409, "Тенант с таким code уже существует")
        raise
    return {"ok": True}

@router.put("/brand/tenants/{tid}")
def upd_tenant(tid: int, p: TenantUpd):
    data = {k: v for k, v in p.model_dump().items() if v is not None}
    if data:
        sets = ", ".join(f"{k}=:{k}" for k in data)
        data["id"] = tid
        with _eng().begin() as c:
            c.execute(text(f"UPDATE tenants SET {sets} WHERE id=:id"), data)
    return {"ok": True}

@router.post("/brand/tenants/{tid}/toggle")
def toggle_tenant(tid: int):
    with _eng().begin() as c:
        c.execute(text("UPDATE tenants SET active = NOT active WHERE id=:id"), {"id": tid})
    return {"ok": True}

@router.get("/brand/summary")
def brand_summary():
    with _eng().begin() as c:
        s = c.execute(text("SELECT * FROM branding_settings WHERE id=1")).mappings().first()
        t = c.execute(text("SELECT COUNT(*) AS n, COUNT(*) FILTER (WHERE active) AS a FROM tenants")).mappings().first()
    return {"settings": dict(s) if s else {}, "tenants_total": t["n"], "tenants_active": t["a"]}
