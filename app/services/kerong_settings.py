"""Настройки Kerong в notification_settings.config (JSONB) + ensure таблицы аренды.
Блок: {"kerong": {"base_url": "...", "bu_board_uuid": "...", "cu_boards": [0,1,2,3]}}"""
import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine

DEFAULT_CU_BOARDS = [0, 1, 2, 3]


def ensure_kerong_tables(db: Session = None) -> None:
    with engine.begin() as c:
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS locker_rentals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                client_id UUID NOT NULL,
                cu_board_id INTEGER NOT NULL,
                lock_number INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )"""))
        c.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS locker_rentals_one_active
            ON locker_rentals(cu_board_id, lock_number) WHERE is_active"""))


def _parse_config(raw) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def get_kerong_settings(db: Session) -> dict:
    ensure_kerong_tables(db)
    row = db.execute(text("SELECT config FROM notification_settings LIMIT 1")).first()
    cfg = _parse_config(row[0] if row else None)
    k = (cfg.get("kerong") or {})
    return {
        "base_url": (k.get("base_url") or "").strip(),
        "bu_board_uuid": (k.get("bu_board_uuid") or "").strip(),
        "cu_boards": [int(x) for x in (k.get("cu_boards") or DEFAULT_CU_BOARDS)],
    }


def save_kerong_settings(db: Session, data: dict) -> dict:
    ensure_kerong_tables(db)
    current = get_kerong_settings(db)
    base_url = (data.get("base_url", current["base_url"]) or "").strip()
    bu_uuid = (data.get("bu_board_uuid", current["bu_board_uuid"]) or "").strip()
    cu = data.get("cu_boards", current["cu_boards"])
    if not isinstance(cu, list) or not all(isinstance(x, int) and 0 <= x <= 9 for x in cu):
        raise ValueError("cu_boards: список номеров плат 0..9")
    block = {"base_url": base_url, "bu_board_uuid": bu_uuid, "cu_boards": cu}
    row = db.execute(text("SELECT config FROM notification_settings LIMIT 1")).first()
    cfg = _parse_config(row[0] if row else None)
    cfg["kerong"] = block
    db.execute(text("UPDATE notification_settings SET config = :c"), {"c": json.dumps(cfg)})
    db.commit()
    return block
