# -*- coding: utf-8 -*-
"""Корзина: просмотр снимков удалённых сущностей и их восстановление."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.api.dependencies import get_current_user

router = APIRouter(prefix="/trash", tags=["trash"])

ALLOWED = {
    "clients",
    "users",
    "tariffs",
    "document_templates",
    "music_zones",
}


def _admin(user):
    if not (
        getattr(user, "is_superuser", False)
        or str(getattr(user, "username", "")).lower() == "superadmin"
    ):
        raise HTTPException(status_code=403, detail="superadmin required")
    return user


@router.get("")
def trash_list(
    entity: str = "",
    limit: int = Query(default=200, ge=1, le=500),
    user=Depends(get_current_user),
):
    _admin(user)

    if entity and entity not in ALLOWED:
        raise HTTPException(status_code=400, detail="unknown entity")

    from app.db.session import engine

    sql = """
        SELECT id::text, entity, entity_id, payload, deleted_at
        FROM deletion_snapshots
        WHERE deleted_at > now() - interval '30 days'
    """
    params = {"limit": limit}

    if entity:
        sql += " AND entity = :entity"
        params["entity"] = entity

    sql += " ORDER BY deleted_at DESC LIMIT :limit"

    with engine.begin() as connection:
        rows = connection.execute(text(sql), params).mappings().all()

    items = []
    for row in rows:
        payload = row["payload"] or {}
        name = (
            (payload.get("last_name") or "")
            + " "
            + (payload.get("first_name") or "")
        ).strip()

        name = (
            name
            or payload.get("username")
            or payload.get("name")
            or payload.get("code")
            or row["entity_id"]
        )

        items.append({
            "id": row["id"],
            "entity": row["entity"],
            "entity_id": row["entity_id"],
            "name": str(name)[:80],
            "deleted_at": row["deleted_at"].isoformat(),
        })

    return {"ok": True, "items": items}


@router.post("/{sid}/restore")
def trash_restore(sid: str, user=Depends(get_current_user)):
    _admin(user)

    from app.db.session import engine

    with engine.begin() as connection:
        snapshot = connection.execute(
            text("""
                SELECT entity, entity_id, payload
                FROM deletion_snapshots
                WHERE id::text = :sid
                FOR UPDATE
            """),
            {"sid": sid},
        ).mappings().first()

        if not snapshot:
            raise HTTPException(status_code=404, detail="snapshot not found")

        entity = snapshot["entity"]
        if entity not in ALLOWED:
            raise HTTPException(status_code=400, detail="entity not restorable")

        # Имена таблиц поступают только из фиксированного ALLOWED.
        # jsonb_populate_record восстанавливает типы столбцов PostgreSQL.
        sql = f'''
            INSERT INTO "{entity}"
            SELECT * FROM jsonb_populate_record(
                NULL::"{entity}",
                CAST(:payload AS jsonb)
            )
            ON CONFLICT (id) DO NOTHING
            RETURNING id
        '''

        restored = connection.execute(
            text(sql),
            {
                "payload": json.dumps(
                    snapshot["payload"] or {},
                    ensure_ascii=False,
                )
            },
        ).first()

        if not restored:
            raise HTTPException(
                status_code=409,
                detail="entity already exists; snapshot kept",
            )

        connection.execute(
            text("DELETE FROM deletion_snapshots WHERE id::text = :sid"),
            {"sid": sid},
        )

    return {
        "ok": True,
        "restored": entity,
        "entity_id": snapshot["entity_id"],
    }
