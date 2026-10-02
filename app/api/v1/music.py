# -*- coding: utf-8 -*-
"""
Music control API v3 — FitIntel Pro.
Автоматизация фона (зоны, плейлисты, расписание, energize от СКУД)
+ DJ-пульт (Deck A/B, кроссфейд, мастер-громкость)
+ Сэмплер (пады 1-8: библиотека сэмплов, очередь событий с подтверждением).
  provider_type = "local_agent" — агент на ПК в зале опрашивает /agent/state и /agent/pads
  provider_type = "external"    — сервер пушит команды на бокс провайдера
DDL ленивый (CREATE TABLE / ALTER ... IF NOT EXISTS), миграции не нужны.
TODO(MVP): admin-эндпоинты без auth — только для тестовой сети!
"""
import datetime
import json
import threading
import urllib.request
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

# Если зависимость сессии в проекте называется иначе — поправьте этот импорт
from app.db.session import get_db

router = APIRouter(prefix="/music", tags=["music"])

# ---------------------------------------------------------------- DDL
_DDL = [
    """
    CREATE TABLE IF NOT EXISTS music_zones (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        provider_type VARCHAR(20) NOT NULL DEFAULT 'local_agent',
        provider_config JSON,
        agent_token VARCHAR(64),
        desired_state VARCHAR(10) NOT NULL DEFAULT 'stopped',
        desired_playlist_id VARCHAR(36),
        volume INTEGER NOT NULL DEFAULT 50,
        dj_state JSON,
        updated_at TIMESTAMP NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS music_playlists (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description VARCHAR(255),
        tracks JSON NOT NULL DEFAULT '[]'::json,
        is_energize BOOLEAN NOT NULL DEFAULT FALSE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS music_schedule (
        id VARCHAR(36) PRIMARY KEY,
        zone_id VARCHAR(36) NOT NULL REFERENCES music_zones(id) ON DELETE CASCADE,
        day_of_week INTEGER NOT NULL DEFAULT -1,
        time_from TIME NOT NULL,
        time_to TIME NOT NULL,
        playlist_id VARCHAR(36),
        volume INTEGER NOT NULL DEFAULT 50
    )
    """,
    "ALTER TABLE music_zones ADD COLUMN IF NOT EXISTS dj_state JSON",
    """
    CREATE TABLE IF NOT EXISTS music_sfx (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        path VARCHAR(255) NOT NULL,
        volume INTEGER NOT NULL DEFAULT 80,
        sort INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS music_pad_events (
        id VARCHAR(36) PRIMARY KEY,
        zone_id VARCHAR(36) NOT NULL,
        sfx_id VARCHAR(36),
        status VARCHAR(10) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP NOT NULL DEFAULT now(),
        acked_at TIMESTAMP
    )
    """,
]


def _ensure(db):
    for stmt in _DDL:
        db.execute(text(stmt))
    db.commit()


def _row(r):
    return dict(r._mapping)


def _get_zone(db, zid):
    _ensure(db)
    r = db.execute(text("SELECT * FROM music_zones WHERE id=:z"), {"z": zid}).first()
    if not r:
        raise HTTPException(404, "зона не найдена")
    return _row(r)


def _cfg(zone):
    c = zone.get("provider_config") or {}
    return json.loads(c) if isinstance(c, str) else c


def _dj(zone):
    c = zone.get("dj_state") or {}
    return json.loads(c) if isinstance(c, str) else c


# ---------------------------------------------------------------- расписание
def _resolve_schedule(db, zone):
    now = datetime.datetime.now()
    rules = db.execute(text(
        "SELECT * FROM music_schedule WHERE zone_id=:z AND (day_of_week=-1 OR day_of_week=:d) ORDER BY time_from"
    ), {"z": zone["id"], "d": now.weekday()}).fetchall()
    cur = now.time()
    for r in rules:
        rule = _row(r)
        if rule["time_from"] <= cur <= rule["time_to"]:
            if (zone["desired_state"] != "playing"
                    or zone["desired_playlist_id"] != rule["playlist_id"]
                    or zone["volume"] != rule["volume"]):
                db.execute(text(
                    "UPDATE music_zones SET desired_state='playing', desired_playlist_id=:p,"
                    " volume=:v, updated_at=now() WHERE id=:z"
                ), {"p": rule["playlist_id"], "v": rule["volume"], "z": zone["id"]})
                db.commit()
                zone.update(desired_state="playing",
                            desired_playlist_id=rule["playlist_id"],
                            volume=rule["volume"])
            return zone
    return zone


# ---------------------------------------------------------------- external push
def _push_external(zone, action, payload=None):
    cfg = _cfg(zone)
    base = cfg.get("base_url")
    if not base:
        print("PUSH SKIP: нет base_url у зоны", zone["name"])
        return
    url = base.rstrip("/") + cfg.get("cmd_path", "/cmd")
    body = json.dumps({"zone": zone["name"], "action": action,
                       "payload": payload or {}}).encode()

    def _do():
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                print("PUSH %s -> %s [%s]" % (action, url, resp.status))
        except Exception as e:
            print("PUSH %s FAIL: %s" % (action, e))

    threading.Thread(target=_do, daemon=True).start()


# ---------------------------------------------------------------- pydantic
class ZoneIn(BaseModel):
    name: str
    provider_type: str = "local_agent"
    provider_config: dict = {}
    agent_token: str | None = None


class PlaylistIn(BaseModel):
    name: str
    description: str = ""
    tracks: list = []
    is_energize: bool = False


class PlayIn(BaseModel):
    playlist_id: str


class VolumeIn(BaseModel):
    level: int = Field(..., ge=0, le=100)


class ScheduleIn(BaseModel):
    zone_id: str
    day_of_week: int = -1
    time_from: str
    time_to: str
    playlist_id: str | None = None
    volume: int = Field(50, ge=0, le=100)


class TrackRef(BaseModel):
    title: str = "Трек"
    path: str                      # абсолютный путь или относительно --lib агента


class DjStateIn(BaseModel):
    deck_a: TrackRef | None = None   # трек на деке A (None = дек свободен)
    deck_b: TrackRef | None = None
    active_deck: str = "A"           # A | B — какой дек в эфире
    crossfade_seconds: float = Field(8.0, ge=0.0, le=30.0)
    master_volume: int = Field(70, ge=0, le=100)


class SfxIn(BaseModel):
    name: str
    path: str
    volume: int = Field(80, ge=0, le=100)
    sort: int = 0


class PadFireIn(BaseModel):
    sfx_id: str


class PadsAckIn(BaseModel):
    event_ids: list


# ---------------------------------------------------------------- зоны
@router.get("/zones")
def zones_list(db=Depends(get_db)):
    _ensure(db)
    return [_row(r) for r in db.execute(text("SELECT * FROM music_zones ORDER BY name")).fetchall()]


@router.post("/zones", status_code=201)
def zone_create(body: ZoneIn, db=Depends(get_db)):
    _ensure(db)
    if body.provider_type not in ("local_agent", "external"):
        raise HTTPException(400, "provider_type: local_agent | external")
    zid = str(uuid.uuid4())
    token = body.agent_token or uuid.uuid4().hex
    db.execute(text(
        "INSERT INTO music_zones (id,name,provider_type,provider_config,agent_token)"
        " VALUES (:i,:n,:t,:c,:tok)"
    ), {"i": zid, "n": body.name, "t": body.provider_type,
        "c": json.dumps(body.provider_config), "tok": token})
    db.commit()
    return {"id": zid, "agent_token": token}


@router.post("/zones/{zid}/play")
def zone_play(zid: str, body: PlayIn, db=Depends(get_db)):
    zone = _get_zone(db, zid)
    if not db.execute(text("SELECT 1 FROM music_playlists WHERE id=:p"),
                      {"p": body.playlist_id}).first():
        raise HTTPException(404, "плейлист не найден")
    db.execute(text(
        "UPDATE music_zones SET desired_state='playing', desired_playlist_id=:p,"
        " updated_at=now() WHERE id=:z"),
        {"p": body.playlist_id, "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        _push_external(zone, "play", {"playlist_id": body.playlist_id})
    return {"ok": True, "zone": zid, "state": "playing"}


@router.post("/zones/{zid}/pause")
def zone_pause(zid: str, db=Depends(get_db)):
    zone = _get_zone(db, zid)
    db.execute(text("UPDATE music_zones SET desired_state='stopped',"
                    " updated_at=now() WHERE id=:z"), {"z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        _push_external(zone, "pause")
    return {"ok": True, "zone": zid, "state": "stopped"}


@router.post("/zones/{zid}/volume")
def zone_volume(zid: str, body: VolumeIn, db=Depends(get_db)):
    zone = _get_zone(db, zid)
    db.execute(text("UPDATE music_zones SET volume=:v, updated_at=now() WHERE id=:z"),
               {"v": body.level, "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        _push_external(zone, "volume", {"level": body.level})
    return {"ok": True, "zone": zid, "volume": body.level}


@router.post("/zones/{zid}/energize")
def zone_energize(zid: str, db=Depends(get_db)):
    """Пиковый режим: энерджи-плейлист + громкость 90. Триггер — потом от СКУД."""
    zone = _get_zone(db, zid)
    r = db.execute(text("SELECT * FROM music_playlists WHERE is_energize=TRUE LIMIT 1")).first()
    if not r:
        raise HTTPException(404, "нет плейлиста с is_energize=true")
    pl = _row(r)
    db.execute(text(
        "UPDATE music_zones SET desired_state='playing', desired_playlist_id=:p,"
        " volume=90, updated_at=now() WHERE id=:z"),
        {"p": pl["id"], "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        _push_external(zone, "energize")
    return {"ok": True, "zone": zid, "playlist": pl["name"], "volume": 90}


@router.get("/zones/{zid}/status")
def zone_status(zid: str, db=Depends(get_db)):
    zone = _get_zone(db, zid)
    pl = None
    if zone["desired_playlist_id"]:
        r = db.execute(text("SELECT id,name FROM music_playlists WHERE id=:p"),
                       {"p": zone["desired_playlist_id"]}).first()
        if r:
            pl = _row(r)
    return {"zone": zone["name"], "state": zone["desired_state"],
            "volume": zone["volume"], "playlist": pl,
            "dj": _dj(zone), "updated_at": str(zone["updated_at"])}


# ---------------------------------------------------------------- DJ-пульт
@router.get("/zones/{zid}/dj")
def dj_get(zid: str, db=Depends(get_db)):
    zone = _get_zone(db, zid)
    d = _dj(zone)
    return {"zone": zid, **(d or {})}


@router.post("/zones/{zid}/dj")
def dj_set(zid: str, body: DjStateIn, db=Depends(get_db)):
    """Состояние пульта: треки на деках, активный дек, кроссфейд, мастер-громкость.
    local_agent — применяет DJ-агент; external — пуш на бокс провайдера
    (контракт команд настраивается в provider_config, TODO: под реальную коробку)."""
    zone = _get_zone(db, zid)
    if body.active_deck not in ("A", "B"):
        raise HTTPException(400, "active_deck: A | B")
    d = {"deck_a": body.deck_a.model_dump() if body.deck_a else None,
         "deck_b": body.deck_b.model_dump() if body.deck_b else None,
         "active_deck": body.active_deck,
         "crossfade_seconds": body.crossfade_seconds,
         "master_volume": body.master_volume}
    db.execute(text("UPDATE music_zones SET dj_state=:d, updated_at=now() WHERE id=:z"),
               {"d": json.dumps(d, ensure_ascii=False), "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        # Контракт для бокса провайдера: dj_load / dj_crossfade / dj_master.
        # Реальный формат команд подгоним под конкретную коробку (provider_config).
        _push_external(zone, "dj_load", {"deck": "A", "track": d["deck_a"]})
        _push_external(zone, "dj_load", {"deck": "B", "track": d["deck_b"]})
        _push_external(zone, "dj_crossfade", {"active": d["active_deck"],
                                              "seconds": d["crossfade_seconds"]})
        _push_external(zone, "dj_master", {"level": d["master_volume"]})
    return {"ok": True, "zone": zid, **d}


# ---------------------------------------------------------------- плейлисты
@router.get("/playlists")
def pl_list(db=Depends(get_db)):
    _ensure(db)
    return [_row(r) for r in db.execute(text("SELECT * FROM music_playlists ORDER BY name")).fetchall()]


@router.post("/playlists", status_code=201)
def pl_create(body: PlaylistIn, db=Depends(get_db)):
    _ensure(db)
    pid = str(uuid.uuid4())
    db.execute(text(
        "INSERT INTO music_playlists (id,name,description,tracks,is_energize)"
        " VALUES (:i,:n,:d,:t,:e)"),
        {"i": pid, "n": body.name, "d": body.description,
         "t": json.dumps(body.tracks, ensure_ascii=False), "e": body.is_energize})
    db.commit()
    return {"id": pid}


@router.delete("/playlists/{pid}", status_code=204)
def pl_delete(pid: str, db=Depends(get_db)):
    _ensure(db)
    db.execute(text("DELETE FROM music_playlists WHERE id=:p"), {"p": pid})
    db.commit()
    return None


# ---------------------------------------------------------------- расписание
@router.get("/schedule")
def sched_list(zone_id: str | None = None, db=Depends(get_db)):
    _ensure(db)
    if zone_id:
        rows = db.execute(text(
            "SELECT * FROM music_schedule WHERE zone_id=:z"
            " ORDER BY day_of_week, time_from"), {"z": zone_id}).fetchall()
    else:
        rows = db.execute(text(
            "SELECT * FROM music_schedule ORDER BY zone_id, day_of_week, time_from")).fetchall()
    return [_row(r) for r in rows]


@router.post("/schedule", status_code=201)
def sched_add(body: ScheduleIn, db=Depends(get_db)):
    _ensure(db)
    _get_zone(db, body.zone_id)
    sid = str(uuid.uuid4())
    db.execute(text(
        "INSERT INTO music_schedule (id,zone_id,day_of_week,time_from,time_to,playlist_id,volume)"
        " VALUES (:i,:z,:d,:f,:t,:p,:v)"),
        {"i": sid, "z": body.zone_id, "d": body.day_of_week, "f": body.time_from,
         "t": body.time_to, "p": body.playlist_id, "v": body.volume})
    db.commit()
    return {"id": sid}


@router.delete("/schedule/{sid}", status_code=204)
def sched_del(sid: str, db=Depends(get_db)):
    _ensure(db)
    db.execute(text("DELETE FROM music_schedule WHERE id=:i"), {"i": sid})
    db.commit()
    return None


# ---------------------------------------------------------------- сэмплер (пады 1-8)
@router.get("/sfx")
def sfx_list(db=Depends(get_db)):
    _ensure(db)
    return [_row(r) for r in db.execute(text("SELECT * FROM music_sfx ORDER BY sort, name")).fetchall()]


@router.post("/sfx", status_code=201)
def sfx_create(body: SfxIn, db=Depends(get_db)):
    _ensure(db)
    sid = str(uuid.uuid4())
    db.execute(text("INSERT INTO music_sfx (id,name,path,volume,sort) VALUES (:i,:n,:p,:v,:s)"),
               {"i": sid, "n": body.name, "p": body.path, "v": body.volume, "s": body.sort})
    db.commit()
    return {"id": sid}


@router.delete("/sfx/{sid}", status_code=204)
def sfx_delete(sid: str, db=Depends(get_db)):
    _ensure(db)
    db.execute(text("DELETE FROM music_sfx WHERE id=:i"), {"i": sid})
    db.commit()
    return None


@router.post("/zones/{zid}/pad-fire")
def pad_fire(zid: str, body: PadFireIn, db=Depends(get_db)):
    """Один-шот сэмпл: событие в очередь (local) или пуш на бокс (external)."""
    zone = _get_zone(db, zid)
    r = db.execute(text("SELECT * FROM music_sfx WHERE id=:i"), {"i": body.sfx_id}).first()
    if not r:
        raise HTTPException(404, "сэмпл не найден")
    sfx = _row(r)
    if zone["provider_type"] == "external":
        _push_external(zone, "pad_fire",
                       {"sfx": {"name": sfx["name"], "path": sfx["path"], "volume": sfx["volume"]}})
        return {"ok": True, "zone": zid, "sfx": sfx["name"], "mode": "external"}
    eid = str(uuid.uuid4())
    db.execute(text("INSERT INTO music_pad_events (id,zone_id,sfx_id) VALUES (:i,:z,:s)"),
               {"i": eid, "z": zid, "s": body.sfx_id})
    db.commit()
    return {"ok": True, "event_id": eid, "zone": zid, "sfx": sfx["name"]}


# ---------------------------------------------------------------- агент
@router.get("/agent/state")
def agent_state(token: str = Query(...), db=Depends(get_db)):
    _ensure(db)
    r = db.execute(text("SELECT * FROM music_zones WHERE agent_token=:t"),
                   {"t": token}).first()
    if not r:
        raise HTTPException(403, "bad token")
    zone = _row(r)
    if zone["provider_type"] != "local_agent":
        raise HTTPException(400, "зона не в режиме local_agent")
    zone = _resolve_schedule(db, zone)
    playlist = None
    if zone["desired_playlist_id"]:
        pr = db.execute(text("SELECT * FROM music_playlists WHERE id=:p"),
                        {"p": zone["desired_playlist_id"]}).first()
        if pr:
            p = _row(pr)
            tracks = p["tracks"]
            if isinstance(tracks, str):
                tracks = json.loads(tracks)
            playlist = {"id": p["id"], "name": p["name"], "tracks": tracks}
    dj = _dj(zone)
    return {"zone_id": zone["id"], "name": zone["name"],
            "state": zone["desired_state"], "volume": zone["volume"],
            "playlist": playlist, "dj": dj or {},
            "server_time": datetime.datetime.now().isoformat(timespec="seconds")}


@router.get("/agent/pads")
def agent_pads(token: str = Query(...), db=Depends(get_db)):
    _ensure(db)
    r = db.execute(text("SELECT * FROM music_zones WHERE agent_token=:t"),
                   {"t": token}).first()
    if not r:
        raise HTTPException(403, "bad token")
    zone = _row(r)
    rows = db.execute(text(
        "SELECT e.id AS event_id, e.sfx_id, s.name, s.path, s.volume"
        " FROM music_pad_events e JOIN music_sfx s ON s.id=e.sfx_id"
        " WHERE e.zone_id=:z AND e.status='pending' ORDER BY e.created_at"),
        {"z": zone["id"]}).fetchall()
    return {"events": [_row(x) for x in rows]}


@router.post("/agent/pads/ack")
def agent_pads_ack(body: PadsAckIn, db=Depends(get_db)):
    for eid in body.event_ids:
        db.execute(text("UPDATE music_pad_events SET status='acked', acked_at=now() WHERE id=:i"),
                   {"i": eid})
    db.execute(text("DELETE FROM music_pad_events WHERE status='acked'"
                    " AND acked_at < now() - interval '1 day'"))
    db.commit()
    return {"ok": True, "acked": len(body.event_ids)}