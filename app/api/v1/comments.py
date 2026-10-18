# app/api/v1/comments.py
"""Комментарии и задачи по клиентам (заметки сотрудников). Таблица client_comments."""
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text as _text
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db

router = APIRouter(tags=["Comments"])


class CommentIn(BaseModel):
    text: str
    type: str = "NOTE"
    due_date: Optional[str] = None  # YYYY-MM-DD


class CommentPatch(BaseModel):
    text: Optional[str] = None
    type: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None


_DDL = """
CREATE TABLE IF NOT EXISTS client_comments (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    author_id UUID,
    text TEXT NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'NOTE',
    due_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
)
"""


def _ensure(db: Session):
    db.execute(_text(_DDL))
    db.commit()


def _uid(current_user):
    if current_user is None:
        return None
    if isinstance(current_user, dict):
        return current_user.get("id")
    return getattr(current_user, "id", None)


def _row(r):
    d = dict(r)
    for k, v in list(d.items()):
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


@router.post("/clients/{client_id}/comments")
def add_comment(client_id: UUID, body: CommentIn,
                current_user=Depends(require_permission("clients.update")),
                db: Session = Depends(get_db)):
    _ensure(db)
    if not db.execute(_text("SELECT 1 FROM clients WHERE id=:i"), {"i": str(client_id)}).first():
        raise HTTPException(404, "Клиент не найден")
    txt = (body.text or "").strip()
    if not txt:
        raise HTTPException(400, "Текст обязателен")
    cid = str(uuid4())
    db.execute(_text(
        "INSERT INTO client_comments (id, client_id, author_id, text, type, due_date) "
        "VALUES (:id, :c, :a, :t, :ty, :d)"),
        {"id": cid, "c": str(client_id), "a": _uid(current_user), "t": txt,
         "ty": (body.type or "NOTE")[:20], "d": body.due_date or None})
    db.commit()
    return {"id": cid}


@router.get("/clients/{client_id}/comments")
def list_client_comments(client_id: UUID,
                         current_user=Depends(require_permission("clients.read")),
                         db: Session = Depends(get_db)):
    _ensure(db)
    rows = db.execute(_text(
        "SELECT c.id, c.client_id, c.text, c.type, c.due_date, c.status, "
        "c.created_at, c.updated_at, "
        "COALESCE(NULLIF(u.full_name, ''), u.username) AS author_name "
        "FROM client_comments c LEFT JOIN users u ON u.id = c.author_id "
        "WHERE c.client_id = :cid ORDER BY c.created_at DESC LIMIT 500"),
        {"cid": str(client_id)}).mappings().all()
    items = [_row(r) for r in rows]
    return {"items": items, "count": len(items)}


@router.get("/comments")
def list_comments(author_id: Optional[str] = None,
                  client_id: Optional[str] = None,
                  from_: Optional[str] = Query(None, alias="from"),
                  to: Optional[str] = None,
                  type: Optional[str] = None,
                  current_user=Depends(require_permission("clients.read")),
                  db: Session = Depends(get_db)):
    _ensure(db)
    sql = ("SELECT c.id, c.client_id, c.text, c.type, c.due_date, c.status, c.created_at, "
           "COALESCE(NULLIF(u.full_name, ''), u.username) AS author_name "
           "FROM client_comments c LEFT JOIN users u ON u.id = c.author_id WHERE 1=1")
    params = {}
    if author_id:
        sql += " AND c.author_id = :a"; params["a"] = author_id
    if client_id:
        sql += " AND c.client_id = :c"; params["c"] = client_id
    if type:
        sql += " AND c.type = :t"; params["t"] = type
    if from_:
        sql += " AND c.created_at::date >= :f"; params["f"] = from_
    if to:
        sql += " AND c.created_at::date <= :tt"; params["tt"] = to
    sql += " ORDER BY c.created_at DESC LIMIT 500"
    rows = db.execute(_text(sql), params).mappings().all()
    items = [_row(r) for r in rows]
    return {"items": items, "count": len(items)}


@router.patch("/comments/{comment_id}")
def patch_comment(comment_id: UUID, body: CommentPatch,
                  current_user=Depends(require_permission("clients.update")),
                  db: Session = Depends(get_db)):
    _ensure(db)
    if not db.execute(_text("SELECT 1 FROM client_comments WHERE id=:i"),
                      {"i": str(comment_id)}).first():
        raise HTTPException(404, "Комментарий не найден")
    fields, params = [], {"i": str(comment_id)}
    if body.text is not None:
        fields.append("text = :t"); params["t"] = body.text.strip()
    if body.type is not None:
        fields.append("type = :ty"); params["ty"] = body.type[:20]
    if body.due_date is not None:
        fields.append("due_date = :d"); params["d"] = body.due_date or None
    if body.status is not None:
        fields.append("status = :s"); params["s"] = body.status[:20]
    if fields:
        fields.append("updated_at = now()")
        db.execute(_text("UPDATE client_comments SET " + ", ".join(fields) + " WHERE id = :i"), params)
        db.commit()
    return {"ok": True}


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: UUID,
                   current_user=Depends(require_permission("clients.update")),
                   db: Session = Depends(get_db)):
    _ensure(db)
    r = db.execute(_text("DELETE FROM client_comments WHERE id = :i RETURNING id"),
                   {"i": str(comment_id)}).first()
    db.commit()
    if not r:
        raise HTTPException(404, "Комментарий не найден")
    return {"ok": True}