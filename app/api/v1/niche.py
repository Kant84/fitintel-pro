"""E40: Нишевые шаблоны (ТЗ v3.2 §4.11).

Готовые конфигурации клуба под ниши (фитнес, йога, единоборства,
танцы, бассейн, кроссфит): пресеты тарифов и услуг, превью,
применение к клубу, клонирование, кастомные шаблоны.
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:  # pragma: no cover
    try:
        from app.core.database import get_db
    except ImportError:
        from app.database import get_db

from app.api.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/niche", tags=["niche"])

_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt(dt):
    return dt.strftime(_FMT)


def _cols(db, table):
    rows = db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _insert(db, table, data):
    cols = _cols(db, table)
    d = {k: v for k, v in data.items() if k in cols}
    names = ", ".join(d.keys())
    params = ", ".join(":" + k for k in d.keys())
    db.execute(text(f"INSERT INTO {table} ({names}) VALUES ({params})"), d)
    return d


def _get_template(db, key):
    row = db.execute(
        text("SELECT * FROM niche_templates WHERE id=:k OR code=:k"), {"k": key}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return dict(row)


def _config(tpl):
    try:
        return json.loads(tpl.get("config") or "{}")
    except Exception:
        return {}


class TemplateCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    config: dict


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None


class ApplyRequest(BaseModel):
    club_id: Optional[str] = None


class CloneRequest(BaseModel):
    new_code: str
    new_name: Optional[str] = None


@router.get("/templates")
def list_templates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(
        text("SELECT * FROM niche_templates ORDER BY is_builtin DESC, created_at")
    ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/templates", status_code=201)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    dup = db.execute(
        text("SELECT id FROM niche_templates WHERE code=:c"), {"c": payload.code}
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Шаблон с таким кодом уже существует")
    tid = str(uuid.uuid4())
    _insert(db, "niche_templates", {
        "id": tid, "code": payload.code, "name": payload.name,
        "description": payload.description,
        "config": json.dumps(payload.config, ensure_ascii=False),
        "is_builtin": 0, "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"template_id": tid, "code": payload.code, "message": "Шаблон создан"}


@router.get("/templates/{key}")
def get_template(key: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    tpl = _get_template(db, key)
    tpl["config"] = _config(tpl)
    return tpl


@router.put("/templates/{key}")
def update_template(key: str, payload: TemplateUpdate,
                    db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    tpl = _get_template(db, key)
    if tpl.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Встроенный шаблон нельзя изменить")
    fields = {}
    if payload.name is not None:
        fields["name"] = payload.name
    if payload.description is not None:
        fields["description"] = payload.description
    if payload.config is not None:
        fields["config"] = json.dumps(payload.config, ensure_ascii=False)
    if fields:
        sets = ", ".join(f"{k}=:{k}" for k in fields)
        fields["tid"] = tpl["id"]
        db.execute(text(f"UPDATE niche_templates SET {sets} WHERE id=:tid"), fields)
        db.commit()
    return {"message": "Шаблон обновлён"}


@router.delete("/templates/{key}", status_code=204)
def delete_template(key: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    tpl = _get_template(db, key)
    if tpl.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Встроенный шаблон нельзя удалить")
    db.execute(text("DELETE FROM niche_templates WHERE id=:i"), {"i": tpl["id"]})
    db.commit()
    return None


@router.get("/templates/{key}/preview")
def preview_template(key: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    tpl = _get_template(db, key)
    cfg = _config(tpl)
    return {"code": tpl["code"], "name": tpl["name"],
            "will_create_tariffs": cfg.get("tariffs", []),
            "will_create_services": cfg.get("services", [])}


@router.post("/templates/{key}/apply", status_code=201)
def apply_template(key: str, payload: ApplyRequest, db: Session = Depends(get_db),
                   user=Depends(require_roles("admin"))):
    tpl = _get_template(db, key)
    cfg = _config(tpl)
    created_tariffs, created_services = [], []
    for t in cfg.get("tariffs", []):
        data = _insert(db, "tariffs", {
            "id": str(uuid.uuid4()),
            "code": "NICH-" + uuid.uuid4().hex[:8].upper(),
            "name": t.get("name"),
            "price": t.get("price"),
            "currency": "RUB",
            "duration_days": t.get("duration_days"),
            "is_unlimited": False,
            "club_id": payload.club_id,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        })
        created_tariffs.append(t.get("name"))
    for s in cfg.get("services", []):
        data = _insert(db, "services", {
            "id": str(uuid.uuid4()),
            "name": s.get("name"),
            "category": tpl["name"],
            "price": s.get("price"),
            "duration_minutes": 60,
            "club_id": payload.club_id,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        })
        created_services.append(s.get("name"))
    result = {"tariffs": created_tariffs, "services": created_services}
    _insert(db, "niche_template_applies", {
        "id": str(uuid.uuid4()), "template_id": tpl["id"], "club_id": payload.club_id,
        "applied_by": str(getattr(user, "id", "") or ""),
        "result": json.dumps(result, ensure_ascii=False),
        "applied_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"template": tpl["code"], "created_tariffs": created_tariffs,
            "created_services": created_services, "message": "Шаблон применён"}


@router.post("/templates/{key}/clone", status_code=201)
def clone_template(key: str, payload: CloneRequest, db: Session = Depends(get_db),
                   user=Depends(require_roles("admin"))):
    tpl = _get_template(db, key)
    dup = db.execute(
        text("SELECT id FROM niche_templates WHERE code=:c"), {"c": payload.new_code}
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Шаблон с таким кодом уже существует")
    tid = str(uuid.uuid4())
    _insert(db, "niche_templates", {
        "id": tid, "code": payload.new_code,
        "name": payload.new_name or (tpl["name"] + " (копия)"),
        "description": tpl.get("description"), "config": tpl.get("config"),
        "is_builtin": 0, "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"template_id": tid, "code": payload.new_code, "message": "Шаблон клонирован"}


@router.get("/applies")
def list_applies(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(
        text("SELECT * FROM niche_template_applies ORDER BY applied_at DESC")
    ).mappings().fetchall()
    return [dict(r) for r in rows]
