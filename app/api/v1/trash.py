# -*- coding: utf-8 -*-
"""Корзина: снимки удалённых сущностей + восстановление (<=30 дней)."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/trash", tags=["trash"])
ALLOWED = {"clients", "tariffs", "document_templates", "music_zones"}


def _admin(user):
    if not (getattr(user, "is_superuser", False)
            or str(getattr(user, "username", "")).lower() == "superadmin"):
        raise HTTPException(403, "superadmin required")
    return user


@router.get("")
def trash_list(entity: str = "", limit: int = 200, user=Depends(get_current_user)):
    _admin(user)
    from app.db.session import engine
    q = """SELECT id::text, entity, entity_id, payload, deleted_at
           FROM deletion_snapshots
           WHERE deleted_at > now() - interval '30 days'"""
    args = {}
    if entity in ALLOWED or entity == "users":
        q += " AND entity = :e"
        args["e"] = entity
    q += " ORDER BY deleted_at DESC LIMIT :lim"
    args["lim"] = min(limit, 500)
    with engine.begin() as c:
        rows = c.execute(text(q), args).mappings().all()
    out = []
    for r in rows:
        p = r["payload"] or {}
        name = (p.get("last_name") or "") + " " + (p.get("first_name") or "")
        name = name.strip() or p.get("username") or p.get("name") or p.get("code") or r["entity_id"]
        out.append({"id": r["id"], "entity": r["entity"], "entity_id": r["entity_id"],
                    "name": str(name)[:80], "deleted_at": r["deleted_at"].isoformat()})
    return {"ok": True, "items": out}


@router.post("/{sid}/restore")
def trash_restore(sid: str, user=Depends(get_current_user)):
    _admin(user)
    from app.db.session import engine
    with engine.begin() as c:
        r = c.execute(text(
            "SELECT entity, payload FROM deletion_snapshots WHERE id::text=:s"),
            {"s": sid}).mappings().first()
        if not r:
            raise HTTPException(404, "snapshot not found")
        entity, payload = r["entity"], dict(r["payload"] or {})
        if entity == "users":
            c.execute(text("""UPDATE users SET deleted_at=NULL, is_active=TRUE,
                username=:u, email=:e, phone=:p, full_name=:f, updated_at=now()
                WHERE id::text=:i"""),
                {"u": payload.get("username"), "e": payload.get("email"),
                 "p": payload.get("phone"), "f": payload.get("full_name"),
                 "i": payload.get("id")})
        elif entity in ALLOWED:
            cols = {x[0] for x in c.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": entity}).fetchall()}
            nn = c.execute(text(
                "SELECT column_name, data_type, column_default FROM information_schema.columns"
                " WHERE table_name=:t AND is_nullable='NO'"), {"t": entity}).all()
            vals = {k: v for k, v in payload.items() if k in cols and v is not None}
            for col, dtp, dflt in nn:
                if col in vals or col == "id" or dflt is not None:
                    continue
                if dtp == "boolean":
                    vals[col] = False
                elif dtp.startswith(("int", "numeric")):
                    vals[col] = 0
                elif dtp.startswith("timestamp"):
                    vals[col] = dt.datetime.now(dt.timezone.utc)
                else:
                    vals[col] = ""
            sql = "INSERT INTO %s (%s) VALUES (%s) ON CONFLICT DO NOTHING" % (
                entity, ", ".join(vals), ", ".join(":" + k for k in vals))
            c.execute(text(sql), vals)
        else:
            raise HTTPException(400, "entity not restorable")
        c.execute(text("DELETE FROM deletion_snapshots WHERE id::text=:s"), {"s": sid})
    return {"ok": True, "restored": entity}
