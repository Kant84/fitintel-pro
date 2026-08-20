"""E42: Documents — массовая генерация + events/signatures/relations (ТЗ v3.2 §13).

Расширение модуля документов (E33): пакетная генерация документов
по списку клиентов, журнал событий жизненного цикла, реестр подписей
сторон, связи документа с объектами (абонемент/платёж/договор/визит),
сводная история документа.
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional

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

router = APIRouter(prefix="/documents", tags=["documents-bulk"])

_FMT = "%Y-%m-%d %H:%M:%S"
_REL_TYPES = ("subscription", "payment", "contract", "visit")


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


def _doc_exists(db, document_id):
    row = db.execute(
        text("SELECT id FROM documents WHERE id=:i"), {"i": document_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Документ не найден")


def _get_client(db, client_id):
    try:
        key = uuid.UUID(str(client_id))
    except (ValueError, AttributeError):
        return None
    row = db.execute(
        text("SELECT id, first_name, last_name, middle_name, phone, email FROM clients WHERE id=:i"),
        {"i": key},
    ).mappings().fetchone()
    return dict(row) if row else None


def _render(template_text, client):
    name = " ".join(p for p in [client.get("last_name"), client.get("first_name"), client.get("middle_name")] if p)
    out = template_text or ""
    out = out.replace("{{client_name}}", name)
    out = out.replace("{{client_phone}}", str(client.get("phone") or ""))
    out = out.replace("{{client_email}}", str(client.get("email") or ""))
    out = out.replace("{{date}}", datetime.now().strftime("%d.%m.%Y"))
    return out


def _event(db, document_id, event_type, actor=None, payload=None):
    _insert(db, "document_events", {
        "id": str(uuid.uuid4()), "document_id": document_id, "event_type": event_type,
        "actor": actor, "payload": payload, "created_at": _fmt(datetime.now()),
    })


class MassGenerateRequest(BaseModel):
    template_id: str
    client_ids: List[str]


class EventCreate(BaseModel):
    event_type: str
    payload: Optional[str] = None


class SignatureCreate(BaseModel):
    signer_name: str
    signer_role: str = "client"
    signature_data: Optional[str] = None


class RelationCreate(BaseModel):
    related_type: str
    related_id: str


@router.post("/mass-generate", status_code=201)
def mass_generate(payload: MassGenerateRequest, db: Session = Depends(get_db),
                  user=Depends(require_roles("admin"))):
    tpl = db.execute(
        text("SELECT * FROM document_templates WHERE id=:i OR code=:i"), {"i": payload.template_id}
    ).mappings().fetchone()
    if not tpl:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    tpl = dict(tpl)
    body = tpl.get("content") or tpl.get("body") or ""
    title = tpl.get("name") or tpl.get("code") or "Документ"
    job_id = str(uuid.uuid4())
    doc_ids, errors, done = [], [], 0
    actor = str(getattr(user, "id", "") or "admin")
    for cid in payload.client_ids:
        client = _get_client(db, cid)
        if not client:
            errors.append(f"{cid}: клиент не найден")
            continue
        doc_id = str(uuid.uuid4())
        _insert(db, "documents", {
            "id": doc_id,
            "doc_type": tpl.get("code") or "contract",
            "title": title,
            "content": _render(body, client),
            "client_id": cid,
            "template_id": str(tpl.get("id")),
            "status": "generated",
            "signed": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        })
        _event(db, doc_id, "created", actor)
        _event(db, doc_id, "generated", actor)
        doc_ids.append(doc_id)
        done += 1
    failed = len(payload.client_ids) - done
    now = _fmt(datetime.now())
    _insert(db, "document_jobs", {
        "id": job_id, "template_id": str(tpl.get("id")), "total": len(payload.client_ids),
        "done": done, "failed": failed, "status": "done",
        "document_ids": json.dumps(doc_ids), "errors": json.dumps(errors, ensure_ascii=False),
        "created_at": now, "finished_at": now,
    })
    db.commit()
    return {"job_id": job_id, "total": len(payload.client_ids), "done": done,
            "failed": failed, "document_ids": doc_ids, "errors": errors,
            "message": "Массовая генерация завершена"}


@router.get("/mass-jobs")
def list_jobs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(
        text("SELECT * FROM document_jobs ORDER BY created_at DESC")
    ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/mass-jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(
        text("SELECT * FROM document_jobs WHERE id=:i"), {"i": job_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    d = dict(row)
    d["document_ids"] = json.loads(d.get("document_ids") or "[]")
    d["errors"] = json.loads(d.get("errors") or "[]")
    return d


@router.get("/{document_id}/events")
def list_events(document_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _doc_exists(db, document_id)
    rows = db.execute(
        text("SELECT * FROM document_events WHERE document_id=:i ORDER BY created_at"),
        {"i": document_id},
    ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/{document_id}/events", status_code=201)
def add_event(document_id: str, payload: EventCreate, db: Session = Depends(get_db),
              user=Depends(get_current_user)):
    _doc_exists(db, document_id)
    actor = str(getattr(user, "id", "") or "user")
    _event(db, document_id, payload.event_type, actor, payload.payload)
    db.commit()
    return {"message": "Событие зафиксировано", "event_type": payload.event_type}


@router.get("/{document_id}/signatures")
def list_signatures(document_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _doc_exists(db, document_id)
    rows = db.execute(
        text("SELECT * FROM document_signatures WHERE document_id=:i ORDER BY signed_at"),
        {"i": document_id},
    ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/{document_id}/signatures", status_code=201)
def add_signature(document_id: str, payload: SignatureCreate, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    _doc_exists(db, document_id)
    dup = db.execute(
        text("SELECT id FROM document_signatures WHERE document_id=:i AND signer_role=:r"),
        {"i": document_id, "r": payload.signer_role},
    ).fetchone()
    if dup:
        raise HTTPException(status_code=400, detail="Подпись этой стороны уже есть")
    sid = str(uuid.uuid4())
    _insert(db, "document_signatures", {
        "id": sid, "document_id": document_id, "signer_name": payload.signer_name,
        "signer_role": payload.signer_role, "signature_data": payload.signature_data,
        "ip_address": "127.0.0.1", "is_valid": 1, "signed_at": _fmt(datetime.now()),
    })
    _event(db, document_id, "signed", payload.signer_name,
           json.dumps({"role": payload.signer_role}, ensure_ascii=False))
    db.commit()
    return {"signature_id": sid, "is_valid": True, "message": "Подпись добавлена"}


@router.delete("/signatures/{signature_id}", status_code=204)
def delete_signature(signature_id: str, db: Session = Depends(get_db),
                     user=Depends(require_roles("admin"))):
    row = db.execute(
        text("SELECT id FROM document_signatures WHERE id=:i"), {"i": signature_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Подпись не найдена")
    db.execute(text("DELETE FROM document_signatures WHERE id=:i"), {"i": signature_id})
    db.commit()
    return None


@router.get("/{document_id}/relations")
def list_relations(document_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _doc_exists(db, document_id)
    rows = db.execute(
        text("SELECT * FROM document_relations WHERE document_id=:i ORDER BY created_at"),
        {"i": document_id},
    ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/{document_id}/relations", status_code=201)
def add_relation(document_id: str, payload: RelationCreate, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    _doc_exists(db, document_id)
    if payload.related_type not in _REL_TYPES:
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип связи")
    rid = str(uuid.uuid4())
    _insert(db, "document_relations", {
        "id": rid, "document_id": document_id, "related_type": payload.related_type,
        "related_id": payload.related_id, "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"relation_id": rid, "message": "Связь добавлена"}


@router.delete("/relations/{relation_id}", status_code=204)
def delete_relation(relation_id: str, db: Session = Depends(get_db),
                    user=Depends(require_roles("admin"))):
    row = db.execute(
        text("SELECT id FROM document_relations WHERE id=:i"), {"i": relation_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Связь не найдена")
    db.execute(text("DELETE FROM document_relations WHERE id=:i"), {"i": relation_id})
    db.commit()
    return None


@router.get("/{document_id}/history")
def document_history(document_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _doc_exists(db, document_id)
    events = db.execute(
        text("SELECT id, event_type AS kind, actor AS who, payload AS details, created_at FROM document_events WHERE document_id=:i"),
        {"i": document_id},
    ).mappings().fetchall()
    sigs = db.execute(
        text("SELECT id, 'signature' AS kind, signer_name AS who, signer_role AS details, signed_at AS created_at FROM document_signatures WHERE document_id=:i"),
        {"i": document_id},
    ).mappings().fetchall()
    rels = db.execute(
        text("SELECT id, 'relation' AS kind, related_type AS who, related_id AS details, created_at FROM document_relations WHERE document_id=:i"),
        {"i": document_id},
    ).mappings().fetchall()
    items = [dict(r) for r in list(events) + list(sigs) + list(rels)]
    items.sort(key=lambda x: x.get("created_at") or "")
    return {"document_id": document_id, "items": items}
