"""E43: Feature Flags advanced (ТЗ v3.2 §4.27, UC-2).

Поверх базового CRUD флагов: percentage/canary rollout
(детерминированный бакет по MD5(user_id:flag_key)), оценка флага
с записью истории, привязка флага к фиче лицензии (UC-2),
статистика оценок, WebSocket-пуш изменений клиентам.
"""
import hashlib
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
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

router = APIRouter(prefix="/feature-flags", tags=["feature-flags-adv"])

_FMT = "%Y-%m-%d %H:%M:%S"
_STRATEGIES = ("percentage", "canary")


class _WSManager:
    def __init__(self):
        self.active = []

    async def connect(self, ws):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
        return len(self.active)


manager = _WSManager()


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


def _get_flag(db, flag_key):
    row = db.execute(
        text("SELECT * FROM feature_flags WHERE flag_key=:k"), {"k": flag_key}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Флаг не найден")
    return dict(row)


def _flag_default_on(flag):
    if not flag.get("is_active"):
        return False
    try:
        return bool(json.loads(flag.get("default_value") or "false"))
    except Exception:
        return str(flag.get("default_value")).strip().lower() in ("true", "1", '"true"')


def _bucket(user_id, flag_key):
    return int(hashlib.md5(f"{user_id}:{flag_key}".encode()).hexdigest(), 16) % 100


def _license_has(db, feature):
    row = db.execute(
        text("SELECT feature FROM ff_license_features WHERE feature=:f"), {"f": feature}
    ).fetchone()
    return row is not None


def _evaluate(db, flag_key, user_id):
    flag = _get_flag(db, flag_key)
    bind = db.execute(
        text("SELECT * FROM ff_license_binds WHERE flag_key=:k"), {"k": flag_key}
    ).mappings().fetchone()
    if bind and bind["required"]:
        if not _license_has(db, bind["license_feature"]):
            return False, "license_denied"
    lic_prefix = "license:ok;" if bind else ""
    rollout = db.execute(
        text("SELECT * FROM ff_rollouts WHERE flag_key=:k"), {"k": flag_key}
    ).mappings().fetchone()
    if not rollout:
        return _flag_default_on(flag), lic_prefix + "default"
    if rollout["strategy"] == "canary":
        users = json.loads(rollout["canary_users"] or "[]")
        return (user_id in users), lic_prefix + "canary"
    b = _bucket(user_id, flag_key)
    return (b < (rollout["percent"] or 0)), lic_prefix + f"percentage:{b}<{rollout['percent']}"


def _record(db, flag_key, user_id, result, reason):
    _insert(db, "ff_evaluations", {
        "id": str(uuid.uuid4()), "flag_key": flag_key, "user_id": user_id,
        "result": 1 if result else 0, "reason": reason, "created_at": _fmt(datetime.now()),
    })


class RolloutSet(BaseModel):
    strategy: str = "percentage"
    percent: int = 100
    canary_users: Optional[List[str]] = None


class LicenseBind(BaseModel):
    license_feature: str
    required: bool = True


class BatchEval(BaseModel):
    user_id: str
    keys: List[str]


class BroadcastMsg(BaseModel):
    key: str


@router.put("/rollout/{flag_key}")
async def set_rollout(flag_key: str, payload: RolloutSet, db: Session = Depends(get_db),
                      user=Depends(require_roles("admin"))):
    _get_flag(db, flag_key)
    if payload.strategy not in _STRATEGIES:
        raise HTTPException(status_code=400, detail="Неизвестная стратегия")
    if payload.percent < 0 or payload.percent > 100:
        raise HTTPException(status_code=400, detail="Некорректный процент")
    existing = db.execute(
        text("SELECT flag_key FROM ff_rollouts WHERE flag_key=:k"), {"k": flag_key}
    ).fetchone()
    users = json.dumps(payload.canary_users or [])
    now = _fmt(datetime.now())
    if existing:
        db.execute(
            text("UPDATE ff_rollouts SET strategy=:s, percent=:p, canary_users=:u, updated_at=:t WHERE flag_key=:k"),
            {"s": payload.strategy, "p": payload.percent, "u": users, "t": now, "k": flag_key},
        )
    else:
        _insert(db, "ff_rollouts", {
            "flag_key": flag_key, "strategy": payload.strategy, "percent": payload.percent,
            "canary_users": users, "updated_at": now,
        })
    db.commit()
    await manager.broadcast({"event": "rollout_changed", "flag_key": flag_key,
                             "strategy": payload.strategy, "percent": payload.percent})
    return {"message": "Rollout сохранён", "flag_key": flag_key,
            "strategy": payload.strategy, "percent": payload.percent}


@router.get("/rollout/{flag_key}")
def get_rollout(flag_key: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_flag(db, flag_key)
    row = db.execute(
        text("SELECT * FROM ff_rollouts WHERE flag_key=:k"), {"k": flag_key}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Rollout не настроен")
    d = dict(row)
    d["canary_users"] = json.loads(d.get("canary_users") or "[]")
    return d


@router.delete("/rollout/{flag_key}", status_code=204)
async def delete_rollout(flag_key: str, db: Session = Depends(get_db),
                         user=Depends(require_roles("admin"))):
    _get_flag(db, flag_key)
    row = db.execute(
        text("SELECT flag_key FROM ff_rollouts WHERE flag_key=:k"), {"k": flag_key}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Rollout не настроен")
    db.execute(text("DELETE FROM ff_rollouts WHERE flag_key=:k"), {"k": flag_key})
    db.commit()
    await manager.broadcast({"event": "rollout_deleted", "flag_key": flag_key})
    return None


@router.get("/evaluate/{flag_key}")
def evaluate(flag_key: str, user_id: str = Query(...), db: Session = Depends(get_db),
             user=Depends(get_current_user)):
    result, reason = _evaluate(db, flag_key, user_id)
    _record(db, flag_key, user_id, result, reason)
    db.commit()
    return {"flag_key": flag_key, "user_id": user_id, "enabled": result, "reason": reason}


@router.post("/evaluate-batch")
def evaluate_batch(payload: BatchEval, db: Session = Depends(get_db), user=Depends(get_current_user)):
    out = {}
    for key in payload.keys:
        result, reason = _evaluate(db, key, payload.user_id)
        _record(db, key, payload.user_id, result, reason)
        out[key] = {"enabled": result, "reason": reason}
    db.commit()
    return {"user_id": payload.user_id, "flags": out}


@router.put("/license-bind/{flag_key}")
def set_license_bind(flag_key: str, payload: LicenseBind, db: Session = Depends(get_db),
                     user=Depends(require_roles("admin"))):
    _get_flag(db, flag_key)
    existing = db.execute(
        text("SELECT flag_key FROM ff_license_binds WHERE flag_key=:k"), {"k": flag_key}
    ).fetchone()
    now = _fmt(datetime.now())
    if existing:
        db.execute(
            text("UPDATE ff_license_binds SET license_feature=:f, required=:r, updated_at=:t WHERE flag_key=:k"),
            {"f": payload.license_feature, "r": 1 if payload.required else 0, "t": now, "k": flag_key},
        )
    else:
        _insert(db, "ff_license_binds", {
            "flag_key": flag_key, "license_feature": payload.license_feature,
            "required": 1 if payload.required else 0, "updated_at": now,
        })
    db.commit()
    return {"message": "Привязка к лицензии сохранена", "flag_key": flag_key,
            "license_feature": payload.license_feature, "required": payload.required}


@router.get("/license-bind/{flag_key}")
def get_license_bind(flag_key: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_flag(db, flag_key)
    row = db.execute(
        text("SELECT * FROM ff_license_binds WHERE flag_key=:k"), {"k": flag_key}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Привязка не настроена")
    return dict(row)


@router.delete("/license-bind/{flag_key}", status_code=204)
def delete_license_bind(flag_key: str, db: Session = Depends(get_db),
                        user=Depends(require_roles("admin"))):
    _get_flag(db, flag_key)
    row = db.execute(
        text("SELECT flag_key FROM ff_license_binds WHERE flag_key=:k"), {"k": flag_key}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Привязка не настроена")
    db.execute(text("DELETE FROM ff_license_binds WHERE flag_key=:k"), {"k": flag_key})
    db.commit()
    return None


@router.get("/stats/{flag_key}")
def flag_stats(flag_key: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_flag(db, flag_key)
    total = db.execute(
        text("SELECT COUNT(*) FROM ff_evaluations WHERE flag_key=:k"), {"k": flag_key}
    ).scalar()
    enabled = db.execute(
        text("SELECT COUNT(*) FROM ff_evaluations WHERE flag_key=:k AND result=1"), {"k": flag_key}
    ).scalar()
    return {"flag_key": flag_key, "evaluations": total, "enabled_count": enabled,
            "enabled_ratio": (enabled / total) if total else 0.0}


@router.post("/test/broadcast")
async def test_broadcast(payload: BroadcastMsg, user=Depends(require_roles("admin"))):
    n = await manager.broadcast({"event": "flag_changed", "flag_key": payload.key})
    return {"message": "Уведомление отправлено", "sent": n}


@router.websocket("/stream")
async def ff_stream(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
