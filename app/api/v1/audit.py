# app/api/v1/audit.py — журнал аудита (экран «История»)
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission

router = APIRouter(prefix="/audit", tags=["Audit"])


def _cleanup(db: Session):
    """Автоочистка записей старше срока хранения (0 = бессрочно)."""
    days = db.execute(text("SELECT retention_days FROM audit_settings WHERE id=1")).scalar()
    if days and int(days) > 0:
        db.execute(text("DELETE FROM audit_logs WHERE created_at < now() - make_interval(days => :d)"),
                   {"d": int(days)})
        db.commit()


@router.get("")
def list_audit(
    entity: str | None = Query(None),
    action: str | None = Query(None),
    actor: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(require_permission("audit.read")),
):
    _cleanup(db)
    where, params = ["1=1"], {}
    if entity:
        where.append("a.entity_type = :entity"); params["entity"] = entity.lower()
    if action:
        where.append("a.action ILIKE :action"); params["action"] = f"%{action}%"
    if actor:
        where.append("u.username ILIKE :actor"); params["actor"] = f"%{actor}%"
    if date_from:
        where.append("a.created_at >= :df"); params["df"] = date_from
    if date_to:
        where.append("a.created_at <= :dt"); params["dt"] = date_to + " 23:59:59"
    params.update({"limit": limit, "offset": offset})
    rows = db.execute(text(f"""
        SELECT a.id,
               to_char(a.created_at AT TIME ZONE 'Europe/Moscow', 'YYYY-MM-DD HH24:MI:SS') AS at,
               COALESCE(u.username, 'system') AS actor,
               a.action, a.entity_type, a.entity_id::text AS entity_id,
               a.status, a.message, a.before_data, a.after_data
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.actor_user_id
        WHERE {' AND '.join(where)}
        ORDER BY a.created_at DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return {"entries": [dict(r) for r in rows]}


class RetentionIn(BaseModel):
    days: int  # 0 = бессрочно


@router.get("/retention")
def get_retention(db: Session = Depends(get_db),
                  user=Depends(require_permission("audit.read"))):
    d = db.execute(text("SELECT retention_days FROM audit_settings WHERE id=1")).scalar()
    return {"days": int(d or 365)}


@router.post("/retention")
def set_retention(payload: RetentionIn, db: Session = Depends(get_db),
                  user=Depends(require_permission("audit.read"))):
    days = max(0, int(payload.days))
    db.execute(text("UPDATE audit_settings SET retention_days = :d WHERE id=1"), {"d": days})
    db.commit()
    _cleanup(db)
    return {"days": days}