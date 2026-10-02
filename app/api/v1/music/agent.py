# -*- coding: utf-8 -*-
"""Endpoint'ы DJ-агента: состояние зоны, очередь падов, подтверждения."""
import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_db
from . import deps

router = APIRouter()


class PadsAckIn(BaseModel):
    event_ids: list


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
    dj = deps.dj_state(zone)
    return {"zone_id": zone["id"], "name": zone["name"],
            "state": zone["desired_state"], "volume": zone["volume"],
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