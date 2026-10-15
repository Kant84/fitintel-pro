#app\api\v1\music\agent.py
# -*- coding: utf-8 -*-
"""Endpoint'ы DJ-агента: состояние зоны, очередь падов, подтверждения,
авто-регистрация плеера по machine_id."""
import datetime
import json
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_db
from . import deps

router = APIRouter()


class PadsAckIn(BaseModel):
    event_ids: list


class RegisterIn(BaseModel):
    machine_id: str
    name: str = ""
    lib: str = ""


@router.post("/agent/register")
def agent_register(body: RegisterIn, db=Depends(get_db)):
    """Авто-регистрация плеера на ПК.

    Если зона с таким machine_id уже есть (и это local_agent) — возвращаем
    её agent_token (идемпотентно, чтобы перезапуск агента не плодил дубли).
    Иначе создаём новую зону local_agent и возвращаем свежий токен.
    """
    deps.ensure(db)
    mid = (body.machine_id or "").strip()
    if not mid:
        raise HTTPException(400, "machine_id обязателен")

    r = db.execute(text(
        "SELECT id, name, agent_token FROM music_zones"
        " WHERE machine_id=:m AND provider_type='local_agent'"),
        {"m": mid}).first()
    if r:
        zone = deps.row(r)
        return {"zone_id": zone["id"], "agent_token": zone["agent_token"],
                "name": zone["name"], "registered": False}

    zid = str(_uuid.uuid4())
    token = _uuid.uuid4().hex
    name = (body.name or "").strip() or ("Зал " + mid[:20])
    db.execute(text(
        "INSERT INTO music_zones (id, name, provider_type, agent_token, machine_id)"
        " VALUES (:i, :n, 'local_agent', :t, :m)"),
        {"i": zid, "n": name, "t": token, "m": mid})
    db.commit()
    return {"zone_id": zid, "agent_token": token,
            "name": name, "registered": True}


@router.get("/agent/state")
def agent_state(token: str = Query(...), db=Depends(get_db)):
    deps.ensure(db)
    r = db.execute(text("SELECT * FROM music_zones WHERE agent_token=:t"),
                   {"t": token}).first()
    if not r:
        raise HTTPException(403, "bad token")
    zone = deps.row(r)
    if zone["provider_type"] != "local_agent":
        raise HTTPException(400, "зона не в режиме local_agent")
    zone = deps.resolve_schedule(db, zone)
    state = zone["desired_state"]

    playlist = None
    if zone["desired_playlist_id"]:
        pr = db.execute(text("SELECT * FROM music_playlists WHERE id=:p"),
                        {"p": zone["desired_playlist_id"]}).first()
        if pr:
            p = deps.row(pr)
            tracks = p["tracks"]
            if isinstance(tracks, str):
                tracks = json.loads(tracks)
            playlist = {"id": p["id"], "name": p["name"], "tracks": tracks}

    # если зона остановлена — не отдаём dj, чтобы агент паузил деки
    dj = deps.dj_state(zone) if state == "playing" else {}

    return {"zone_id": zone["id"], "name": zone["name"],
            "state": state, "volume": zone["volume"],
            "playlist": playlist, "dj": dj or {},
            "server_time": datetime.datetime.now().isoformat(timespec="seconds")}


@router.get("/agent/pads")
def agent_pads(token: str = Query(...), db=Depends(get_db)):
    deps.ensure(db)
    r = db.execute(text("SELECT * FROM music_zones WHERE agent_token=:t"),
                   {"t": token}).first()
    if not r:
        raise HTTPException(403, "bad token")
    zone = deps.row(r)
    rows = db.execute(text(
        "SELECT e.id AS event_id, e.sfx_id, s.name, s.path, s.volume"
        " FROM music_pad_events e JOIN music_sfx s ON s.id=e.sfx_id"
        " WHERE e.zone_id=:z AND e.status='pending' ORDER BY e.created_at"),
        {"z": zone["id"]}).fetchall()
    return {"events": [deps.row(x) for x in rows]}


@router.post("/agent/pads/ack")
def agent_pads_ack(body: PadsAckIn, db=Depends(get_db)):
    for eid in body.event_ids:
        db.execute(text("UPDATE music_pad_events SET status='acked', acked_at=now()"
                        " WHERE id=:i"), {"i": eid})
    db.execute(text("DELETE FROM music_pad_events WHERE status='acked'"
                    " AND acked_at < now() - interval '1 day'"))
    db.commit()
    return {"ok": True, "acked": len(body.event_ids)}