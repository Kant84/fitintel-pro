# app/api/v1/connectors.py — внешние коннекторы клубных систем (E59)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.connectors import get_connector, sync_entity

router = APIRouter(prefix="/connectors", tags=["Connectors"])


class ConnectorIn(BaseModel):
    name: str
    type: str                      # 'fitness1c' | 'hit'
    base_url: str
    auth_login: str = ""
    auth_password: str = ""
    is_active: bool = True


def _row(r) -> dict:
    return {"id": str(r[0]), "name": r[1], "type": r[2], "base_url": r[3],
            "auth_login": r[4] or "", "has_password": bool(r[5]),
            "is_active": bool(r[6]), "last_sync_at": str(r[7] or ""),
            "last_status": r[8] or "", "last_message": r[9] or ""}


@router.get("")
def list_connectors(db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT id, name, type, base_url, auth_login, auth_password, is_active, "
        "last_sync_at, last_status, last_message FROM connectors ORDER BY created_at")).all()
    return {"connectors": [_row(r) for r in rows]}


@router.post("", status_code=201)
def create_connector(data: ConnectorIn, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    rid = db.execute(text(
        "INSERT INTO connectors (name, type, base_url, auth_login, auth_password, is_active) "
        "VALUES (:n, :t, :u, :l, :p, :a) RETURNING id"),
        {"n": data.name, "t": data.type.lower(), "u": data.base_url.rstrip("/"),
         "l": data.auth_login, "p": data.auth_password, "a": data.is_active}).scalar()
    db.commit()
    return {"id": str(rid), "status": "created"}


@router.delete("/{cid}")
def delete_connector(cid: str, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    db.execute(text("DELETE FROM connectors WHERE id=:id"), {"id": cid})
    db.commit()
    return {"status": "deleted"}


def _load(db, cid):
    r = db.execute(text(
        "SELECT id, type, base_url, auth_login, auth_password FROM connectors WHERE id=:id"),
        {"id": cid}).first()
    if not r:
        raise HTTPException(404, "Коннектор не найден")
    return r


@router.post("/{cid}/test")
def test_connector(cid: str, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    r = _load(db, cid)
    conn = get_connector(r[1], r[2], r[3] or "", r[4] or "")
    try:
        res = conn.test_connection()
        return {"status": "ok", **(res if isinstance(res, dict) else {})}
    except Exception as e:
        raise HTTPException(502, f"Соединение не удалось: {str(e)[:300]}")


@router.post("/{cid}/sync")
def sync_connector(cid: str, entity: str = "all",
                   date_from: str | None = None, date_to: str | None = None,
                   db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    r = _load(db, cid)
    conn = get_connector(r[1], r[2], r[3] or "", r[4] or "")
    results = []
    entities = ["clients", "subscriptions", "visits"] if entity == "all" else [entity]
    for ent in entities:
        try:
            rows = (conn.fetch_visits(date_from, date_to) if ent == "visits"
                    else getattr(conn, f"fetch_{ent}")())
            results.append(sync_entity(db, cid, ent, rows))
        except Exception as e:
            results.append({"entity": ent, "status": "error", "message": str(e)[:300]})
    return {"connector_id": cid, "results": results}


@router.get("/{cid}/log")
def connector_log(cid: str, limit: int = 50, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT entity, records_count, status, message, created_at FROM connector_sync_log "
        "WHERE connector_id=:id ORDER BY created_at DESC LIMIT :l"),
        {"id": cid, "l": limit}).all()
    return {"entries": [{"entity": x[0], "records": x[1], "status": x[2],
                         "message": x[3], "at": str(x[4])[:19]} for x in rows]}