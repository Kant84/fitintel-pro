"""E45: Video Analytics advanced (ТЗ v3.2 E12).

Тревожные триггеры (проникновение, скопление, падение, tailgating),
обучение триггеров с feedback-loop (ложное срабатывание -> дообучение),
ONVIF-автообнаружение камер, события тревог с подтверждением.
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/video-ai", tags=["video-ai"])

_FMT = "%Y-%m-%d %H:%M:%S"
_EVENT_TYPES = ("intrusion", "loitering", "crowd", "fall", "tailgating")
# Эмуляция ONVIF discovery (в проде — WS-Discovery probe 3702/udp)
_ONVIF_FOUND = [
    {"name": "ONVIF Cam 1", "ip": "192.168.1.64", "onvif_port": 80},
    {"name": "ONVIF Cam 2", "ip": "192.168.1.65", "onvif_port": 8080},
]


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


def _get_trigger(db, trigger_id):
    row = db.execute(
        text("SELECT * FROM video_triggers WHERE id=:i"), {"i": trigger_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Триггер не найден")
    return dict(row)


def _get_event(db, event_id):
    row = db.execute(
        text("SELECT * FROM video_trigger_events WHERE id=:i"), {"i": event_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    return dict(row)


class TriggerCreate(BaseModel):
    name: str
    event_type: str
    zone: Optional[str] = None
    camera_id: Optional[str] = None
    threshold: float = 0.7


class TriggerUpdate(BaseModel):
    name: Optional[str] = None
    zone: Optional[str] = None
    camera_id: Optional[str] = None
    threshold: Optional[float] = None


class LearnRequest(BaseModel):
    samples: int = 10


class EventCreate(BaseModel):
    trigger_id: str
    camera_id: Optional[str] = None
    confidence: float = 0.9
    snapshot_url: Optional[str] = None


class CameraAdd(BaseModel):
    name: str
    ip: str
    onvif_port: int = 80
    rtsp_url: Optional[str] = None


@router.post("/triggers", status_code=201)
def create_trigger(payload: TriggerCreate, db: Session = Depends(get_db),
                   user=Depends(require_roles("admin"))):
    if payload.event_type not in _EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Неизвестный тип события")
    if not (0 < payload.threshold <= 1):
        raise HTTPException(status_code=400, detail="Порог должен быть в (0, 1]")
    tid = str(uuid.uuid4())
    _insert(db, "video_triggers", {
        "id": tid, "name": payload.name, "event_type": payload.event_type,
        "zone": payload.zone, "camera_id": payload.camera_id,
        "threshold": payload.threshold, "is_active": 1, "learn_samples": 0,
        "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"trigger_id": tid, "event_type": payload.event_type, "message": "Триггер создан"}


@router.get("/triggers")
def list_triggers(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(text("SELECT * FROM video_triggers ORDER BY created_at DESC")).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/triggers/{trigger_id}")
def get_trigger(trigger_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_trigger(db, trigger_id)


@router.put("/triggers/{trigger_id}")
def update_trigger(trigger_id: str, payload: TriggerUpdate,
                   db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_trigger(db, trigger_id)
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "threshold" in fields and not (0 < fields["threshold"] <= 1):
        raise HTTPException(status_code=400, detail="Порог должен быть в (0, 1]")
    if fields:
        sets = ", ".join(f"{k}=:{k}" for k in fields)
        fields["tid"] = trigger_id
        db.execute(text(f"UPDATE video_triggers SET {sets} WHERE id=:tid"), fields)
        db.commit()
    return {"message": "Триггер обновлён"}


@router.post("/triggers/{trigger_id}/learn")
def learn_trigger(trigger_id: str, payload: LearnRequest, db: Session = Depends(get_db),
                  user=Depends(require_roles("admin"))):
    t = _get_trigger(db, trigger_id)
    if payload.samples < 1:
        raise HTTPException(status_code=400, detail="Число примеров должно быть >= 1")
    samples = (t.get("learn_samples") or 0) + payload.samples
    threshold = min(0.99, (t.get("threshold") or 0.7) + payload.samples * 0.005)
    db.execute(
        text("UPDATE video_triggers SET learn_samples=:s, threshold=:th WHERE id=:i"),
        {"s": samples, "th": threshold, "i": trigger_id},
    )
    db.commit()
    return {"message": "Триггер переобучен", "learn_samples": samples, "threshold": threshold}


@router.post("/triggers/{trigger_id}/activate")
def activate_trigger(trigger_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_trigger(db, trigger_id)
    db.execute(text("UPDATE video_triggers SET is_active=1 WHERE id=:i"), {"i": trigger_id})
    db.commit()
    return {"message": "Триггер активирован"}


@router.post("/triggers/{trigger_id}/deactivate")
def deactivate_trigger(trigger_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_trigger(db, trigger_id)
    db.execute(text("UPDATE video_triggers SET is_active=0 WHERE id=:i"), {"i": trigger_id})
    db.commit()
    return {"message": "Триггер деактивирован"}


@router.delete("/triggers/{trigger_id}", status_code=204)
def delete_trigger(trigger_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_trigger(db, trigger_id)
    db.execute(text("DELETE FROM video_trigger_events WHERE trigger_id=:i"), {"i": trigger_id})
    db.execute(text("DELETE FROM video_triggers WHERE id=:i"), {"i": trigger_id})
    db.commit()
    return None


@router.post("/events", status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = _get_trigger(db, payload.trigger_id)
    if not t.get("is_active"):
        raise HTTPException(status_code=400, detail="Триггер не активен")
    if payload.confidence < (t.get("threshold") or 0.7):
        raise HTTPException(status_code=400, detail="Уверенность ниже порога триггера")
    eid = str(uuid.uuid4())
    _insert(db, "video_trigger_events", {
        "id": eid, "trigger_id": payload.trigger_id,
        "camera_id": payload.camera_id or t.get("camera_id"),
        "confidence": payload.confidence,
        "snapshot_url": payload.snapshot_url or f"/snapshots/{eid}.jpg",
        "status": "new", "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"event_id": eid, "status": "new", "message": "Тревожное событие создано"}


@router.get("/events")
def list_events(status: Optional[str] = Query(None), trigger_id: Optional[str] = Query(None),
                db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = "SELECT * FROM video_trigger_events WHERE 1=1"
    params = {}
    if status:
        q += " AND status=:s"
        params["s"] = status
    if trigger_id:
        q += " AND trigger_id=:t"
        params["t"] = trigger_id
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/events/stats")
def events_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    total = db.execute(text("SELECT COUNT(*) FROM video_trigger_events")).scalar()
    by_status = {}
    for r in db.execute(text("SELECT status, COUNT(*) FROM video_trigger_events GROUP BY status")).fetchall():
        by_status[r[0]] = r[1]
    reviewed = by_status.get("confirmed", 0) + by_status.get("false_alarm", 0)
    far = (by_status.get("false_alarm", 0) / reviewed) if reviewed else 0.0
    return {"total": total, "by_status": by_status, "false_alarm_rate": round(far, 4)}


@router.post("/events/{event_id}/confirm")
def confirm_event(event_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    e = _get_event(db, event_id)
    if e["status"] != "new":
        raise HTTPException(status_code=400, detail="Событие уже обработано")
    db.execute(
        text("UPDATE video_trigger_events SET status='confirmed', reviewed_by=:u WHERE id=:i"),
        {"u": str(getattr(user, "id", "") or "user"), "i": event_id},
    )
    db.commit()
    return {"message": "Тревога подтверждена", "status": "confirmed"}


@router.post("/events/{event_id}/false-alarm")
def false_alarm(event_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    e = _get_event(db, event_id)
    if e["status"] != "new":
        raise HTTPException(status_code=400, detail="Событие уже обработано")
    db.execute(
        text("UPDATE video_trigger_events SET status='false_alarm', reviewed_by=:u WHERE id=:i"),
        {"u": str(getattr(user, "id", "") or "user"), "i": event_id},
    )
    # feedback-loop: ложное срабатывание дообучает триггер
    db.execute(
        text("UPDATE video_triggers SET learn_samples=learn_samples+1, threshold=LEAST(0.99, threshold+0.005) WHERE id=:i"),
        {"i": e["trigger_id"]},
    )
    db.commit()
    return {"message": "Отмечено как ложное; триггер дообучен", "status": "false_alarm"}


@router.post("/cameras/discover")
def discover_cameras(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    added, found = [], 0
    for cam in _ONVIF_FOUND:
        found += 1
        dup = db.execute(
            text("SELECT id FROM video_cameras WHERE ip=:ip"), {"ip": cam["ip"]}
        ).fetchone()
        if not dup:
            _insert(db, "video_cameras", {
                "id": str(uuid.uuid4()), "name": cam["name"], "ip": cam["ip"],
                "onvif_port": cam["onvif_port"],
                "rtsp_url": f"rtsp://{cam['ip']}:554/stream1",
                "status": "online", "discovered_via": "onvif",
                "created_at": _fmt(datetime.now()),
            })
            added.append(cam["ip"])
    db.commit()
    return {"found": found, "added": len(added), "added_ips": added,
            "message": "ONVIF-сканирование завершено"}


@router.get("/cameras")
def list_cameras(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(text("SELECT * FROM video_cameras ORDER BY created_at")).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/cameras", status_code=201)
def add_camera(payload: CameraAdd, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    dup = db.execute(text("SELECT id FROM video_cameras WHERE ip=:ip"), {"ip": payload.ip}).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Камера с таким IP уже добавлена")
    cid = str(uuid.uuid4())
    _insert(db, "video_cameras", {
        "id": cid, "name": payload.name, "ip": payload.ip, "onvif_port": payload.onvif_port,
        "rtsp_url": payload.rtsp_url or f"rtsp://{payload.ip}:554/stream1",
        "status": "online", "discovered_via": "manual", "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"camera_id": cid, "message": "Камера добавлена"}
