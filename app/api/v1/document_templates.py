"""Document templates CRUD (admin-created reusable templates)."""
import json, logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

_engine = None
def _eng():
    global _engine
    if _engine is None:
        for mod in ("app.db.session", "app.core.database", "app.database"):
            try:
                m = __import__(mod, fromlist=["engine"])
                _engine = getattr(m, "engine")
                break
            except Exception:
                continue
    if _engine is None:
        raise HTTPException(500, "DB engine not found")
    return _engine

def _ensure():
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS document_templates (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) UNIQUE,
            name VARCHAR(255) NOT NULL,
            doc_type VARCHAR(64) DEFAULT 'contract',
            content TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )"""))
        c.execute(text("""INSERT INTO document_templates (code, name, doc_type, content)
            SELECT 'contract_std', 'Договор (стандартный)', 'contract',
            'ДОГОВОР №____\nг. ____________\n\nКлиент: {client}\nТариф: {tariff}\nСрок: {days} дн.\n\nПодпись: ________'
            WHERE NOT EXISTS (SELECT 1 FROM document_templates WHERE code='contract_std')"""))

class TemplateIn(BaseModel):
    name: str
    doc_type: str = "contract"
    content: str = ""

@router.get("")
@router.get("/")
def list_templates(user=Depends(get_current_user)):
    _ensure()
    with _eng().connect() as c:
        rows = c.execute(text("SELECT id, code, name, doc_type, content, created_at FROM document_templates ORDER BY id")).mappings().all()
    return [dict(r) for r in rows]

@router.post("")
@router.post("/")
def create_template(body: TemplateIn, user=Depends(get_current_user)):
    _ensure()
    import re as _re
    code = _re.sub(r"[^a-z0-9_]+", "_", (body.name or "tpl").lower())[:60] or "tpl"
    with _eng().begin() as c:
        c.execute(text("INSERT INTO document_templates (code, name, doc_type, content) VALUES (:c,:n,:t,:ct) ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name, doc_type=EXCLUDED.doc_type, content=EXCLUDED.content"),
                  {"c": code, "n": body.name, "t": body.doc_type, "ct": body.content})
    return {"ok": True, "code": code}

@router.delete("/{tpl_id}")
def delete_template(tpl_id: int, user=Depends(get_current_user)):
    _ensure()
    with _eng().begin() as c:
        c.execute(text("DELETE FROM document_templates WHERE id=:i"), {"i": tpl_id})
    return {"ok": True}
