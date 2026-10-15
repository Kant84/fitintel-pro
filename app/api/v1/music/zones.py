# -*- coding: utf-8 -*-
"""Зоны: CRUD, play/pause/volume/energize/status."""
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.session import get_db
from . import deps
from . import license

router = APIRouter()


class ZoneIn(BaseModel):
    name: str
    provider_type: str = "local_agent"       # local_agent | external
    provider_config: dict = {}
    agent_token: str | None = None


class PlayIn(BaseModel):
    playlist_id: str


class VolumeIn(BaseModel):
    level: int = Field(..., ge=0, le=100)


@router.get("/zones")
def zones_list(db=Depends(get_db)):
    deps.ensure(db)
    return [deps.row(r) for r in db.execute(
        text("SELECT * FROM music_zones ORDER BY name")).fetchall()]


@router.post("/zones", status_code=201)
def zone_create(body: ZoneIn, db=Depends(get_db)):
    deps.ensure(db)
    if body.provider_type not in ("local_agent", "external"):
        raise HTTPException(400, "provider_type: local_agent | external")
    zid = str(uuid.uuid4())
    token = body.agent_token or uuid.uuid4().hex
    db.execute(text(
        "INSERT INTO music_zones (id,name,provider_type,provider_config,agent_token)"
        " VALUES (:i,:n,:t,:c,:tok)"),
        {"i": zid, "n": body.name, "t": body.provider_type,
         "c": __import__("json").dumps(body.provider_config), "tok": token})
    db.commit()
    return {"id": zid, "agent_token": token}


@router.delete("/zones/{zid}", status_code=204)
def zone_delete(zid: str, db=Depends(get_db)):
    """Удаление зоны (вместе с её расписанием — CASCADE)."""
    deps.get_zone(db, zid)
    db.execute(text("DELETE FROM music_zones WHERE id=:z"), {"z": zid})
    db.commit()
    return None

class ZoneUpdateIn(BaseModel):
    name: str | None = None
    provider_config: dict | None = None


@router.patch("/zones/{zid}")
def zone_update(zid: str, body: ZoneUpdateIn, db=Depends(get_db)):
    """Обновление зоны (имя, provider_config) — настройка провайдера из desktop."""
    deps.get_zone(db, zid)
    if body.name:
        db.execute(text("UPDATE music_zones SET name=:n, updated_at=now() WHERE id=:z"),
                   {"n": body.name, "z": zid})
    if body.provider_config is not None:
        db.execute(text("UPDATE music_zones SET provider_config=:c, updated_at=now() WHERE id=:z"),
                   {"c": json.dumps(body.provider_config), "z": zid})
    db.commit()
    return {"ok": True, "zone": zid}

@router.post("/zones/{zid}/play")
def zone_play(zid: str, body: PlayIn, db=Depends(get_db)):
    zone = deps.get_zone(db, zid)
    license.enforce(db)
    if not db.execute(text("SELECT 1 FROM music_playlists WHERE id=:p"),
                      {"p": body.playlist_id}).first():
        raise HTTPException(404, "плейлист не найден")
    db.execute(text(
        "UPDATE music_zones SET desired_state='playing', desired_playlist_id=:p,"
        " updated_at=now() WHERE id=:z"),
        {"p": body.playlist_id, "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        deps.push_external(zone, "play", {"playlist_id": body.playlist_id})
    return {"ok": True, "zone": zid, "state": "playing"}


@router.post("/zones/{zid}/pause")
def zone_pause(zid: str, db=Depends(get_db)):
    zone = deps.get_zone(db, zid)
    db.execute(text("UPDATE music_zones SET desired_state='stopped',"
                    " updated_at=now() WHERE id=:z"), {"z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        deps.push_external(zone, "pause")
    return {"ok": True, "zone": zid, "state": "stopped"}


@router.post("/zones/{zid}/volume")
def zone_volume(zid: str, body: VolumeIn, db=Depends(get_db)):
    zone = deps.get_zone(db, zid)
    db.execute(text("UPDATE music_zones SET volume=:v, updated_at=now() WHERE id=:z"),
               {"v": body.level, "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        deps.push_external(zone, "volume", {"level": body.level})
    return {"ok": True, "zone": zid, "volume": body.level}


@router.post("/zones/{zid}/energize")
def zone_energize(zid: str, db=Depends(get_db)):
    """Пиковый режим: энерджи-плейлист + громкость 90. Триггер — потом от СКУД."""
    zone = deps.get_zone(db, zid)
    license.enforce(db)
    r = db.execute(text("SELECT * FROM music_playlists WHERE is_energize=TRUE LIMIT 1")).first()
    if not r:
        raise HTTPException(404, "нет плейлиста с is_energize=true")
    pl = deps.row(r)
    db.execute(text(
        "UPDATE music_zones SET desired_state='playing', desired_playlist_id=:p,"
        " volume=90, updated_at=now() WHERE id=:z"),
        {"p": pl["id"], "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        deps.push_external(zone, "energize")
    return {"ok": True, "zone": zid, "playlist": pl["name"], "volume": 90}


@router.get("/zones/{zid}/status")
def zone_status(zid: str, db=Depends(get_db)):
    zone = deps.get_zone(db, zid)
    pl = None
    if zone["desired_playlist_id"]:
        r = db.execute(text("SELECT id,name FROM music_playlists WHERE id=:p"),
                       {"p": zone["desired_playlist_id"]}).first()
        if r:
            pl = deps.row(r)
    return {"zone": zone["name"], "state": zone["desired_state"],
            "volume": zone["volume"], "playlist": pl,
            "dj": deps.dj_state(zone), "updated_at": str(zone["updated_at"])}