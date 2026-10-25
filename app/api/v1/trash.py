# -*- coding: utf-8 -*-
"""Корзина: просмотр снимков удалённых сущностей и их восстановление."""
import json
from urllib.parse import quote

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
    "documents",
    "subscriptions",
    "credentials",
    "bonus_rules",
    "staff_positions",
    "connectors",
    "roles",
    "music_playlists",
    "music_schedule",
    "music_sfx",
    "client_contacts",
    "client_cars",
}


def _admin(user):
    if not (
        getattr(user, "is_superuser", False)
        or str(getattr(user, "username", "")).lower() == "superadmin"
    ):
        raise HTTPException(status_code=403, detail="superadmin required")
    return user


def _undo_path(entity, entity_id, payload):
    """Path of the inverse deletion used by global desktop Undo."""
    value = quote(str(payload.get("code") if entity == "tariffs" else entity_id), safe="")
    routes = {
        "clients": "/clients/%s",
        "users": "/users/%s",
        "tariffs": "/tariffs/%s",
        "document_templates": "/document-templates/%s",
        "music_zones": "/zones/%s",
        "documents": "/documents/%s",
        "subscriptions": "/subscriptions/%s",
        "credentials": "/credentials/%s",
        "bonus_rules": "/bonus-rules/%s",
        "staff_positions": "/staff/positions/%s",
        "connectors": "/connectors/%s",
        "roles": "/roles/%s",
        "music_playlists": "/playlists/%s",
        "music_schedule": "/schedule/%s",
        "music_sfx": "/sfx/%s",
    }
    if entity in ("client_contacts", "client_cars"):
        collection = "contacts" if entity == "client_contacts" else "cars"
        return "/analytics/clients/%s/%s/%s" % (
            quote(str(payload.get("client_id") or ""), safe=""), collection, value,
        )
    template = routes.get(entity)
    return template % value if template else None


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

        payload = snapshot["payload"] or {}
        payload_json = json.dumps(payload, ensure_ascii=False)
        restored = None

        if entity == "clients":
            # A soft-deleted client still exists; restore its original state.
            restored = connection.execute(
                text("""
                    UPDATE clients
                    SET is_active = COALESCE(
                            (CAST(:payload AS jsonb)->>'is_active')::boolean,
                            TRUE
                        ),
                        status = COALESCE(
                            CAST(:payload AS jsonb)->>'status',
                            'ACTIVE'
                        ),
                        deleted_at = NULL,
                        updated_at = now()
                    WHERE id::text = :entity_id
                    RETURNING id
                """),
                {"payload": payload_json, "entity_id": snapshot["entity_id"]},
            ).first()

        elif entity == "users":
            # User deletion anonymizes the existing row instead of physically
            # deleting it. Restore login, e-mail, active flag and original hash.
            restored = connection.execute(
                text("""
                    UPDATE users
                    SET username = CAST(:payload AS jsonb)->>'username',
                        email = CAST(:payload AS jsonb)->>'email',
                        is_active = COALESCE(
                            (CAST(:payload AS jsonb)->>'is_active')::boolean,
                            TRUE
                        ),
                        deleted_at = NULL,
                        password_hash = COALESCE(
                            CAST(:payload AS jsonb)->>'password_hash',
                            password_hash
                        )
                    WHERE id::text = :entity_id
                    RETURNING id
                """),
                {"payload": payload_json, "entity_id": snapshot["entity_id"]},
            ).first()

            if not restored:
                restored = connection.execute(
                    text("""
                        INSERT INTO users
                        SELECT * FROM jsonb_populate_record(
                            NULL::users,
                            CAST(:payload AS jsonb) - '_roles'
                        )
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id
                    """),
                    {"payload": payload_json},
                ).first()

            if restored:
                connection.execute(
                    text("DELETE FROM user_roles WHERE user_id::text = :entity_id"),
                    {"entity_id": snapshot["entity_id"]},
                )
                connection.execute(
                    text("""
                        INSERT INTO user_roles
                        SELECT (parsed.role_row).*
                        FROM (
                            SELECT jsonb_populate_record(
                                NULL::user_roles, value
                            ) AS role_row
                            FROM jsonb_array_elements(
                                COALESCE(
                                    CAST(:payload AS jsonb)->'_roles',
                                    '[]'::jsonb
                                )
                            )
                        ) AS parsed
                        ON CONFLICT DO NOTHING
                    """),
                    {"payload": payload_json},
                )

        else:
            restored = connection.execute(
                text(f"""
                    INSERT INTO "{entity}"
                    SELECT * FROM jsonb_populate_record(
                        NULL::"{entity}",
                        CAST(:payload AS jsonb)
                    )
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
                """),
                {"payload": payload_json},
            ).first()

        # A physically deleted client/user may be restored by the generic INSERT.
        if not restored and entity in ("clients", "users"):
            restored = connection.execute(
                text(f"""
                    INSERT INTO "{entity}"
                    SELECT * FROM jsonb_populate_record(
                        NULL::"{entity}",
                        CAST(:payload AS jsonb) - '_roles'
                    )
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
                """),
                {"payload": payload_json},
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
        "undo_path": _undo_path(entity, snapshot["entity_id"], payload),
    }
