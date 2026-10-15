#app\api\v1\music\dj.py
# -*- coding: utf-8 -*-
"""DJ-пульт: состояние деков A/B, кроссфейд, мастер-громкость, эквалайзер.
local_agent — применяет DJ-агент; external — пуш на бокс провайдера."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.session import get_db
from . import deps

router = APIRouter()


class TrackRef(BaseModel):
    title: str = "Трек"
    path: str                      # абсолютный путь или относительно --lib агента


class DjStateIn(BaseModel):
    deck_a: TrackRef | None = None   # трек на деке A (None = дек свободен)
    deck_b: TrackRef | None = None
    active_deck: str = "A"           # A | B — какой дек в эфире
    crossfade_seconds: float = Field(8.0, ge=0.0, le=30.0)
    master_volume: int = Field(70, ge=0, le=100)
    eq: dict = {}   # {"A": {"bass": 0, "mid": 0, "treble": 0}, "B": {...}}, дБ -12..+12


@router.get("/zones/{zid}/dj")
def dj_get(zid: str, db=Depends(get_db)):
    zone = deps.get_zone(db, zid)
    d = deps.dj_state(zone)
    return {"zone": zid, **(d or {})}


@router.post("/zones/{zid}/dj")
def dj_set(zid: str, body: DjStateIn, db=Depends(get_db)):
    zone = deps.get_zone(db, zid)
    if body.active_deck not in ("A", "B"):
        raise HTTPException(400, "active_deck: A | B")
    d = {"deck_a": body.deck_a.model_dump() if body.deck_a else None,
         "deck_b": body.deck_b.model_dump() if body.deck_b else None,
         "active_deck": body.active_deck,
         "crossfade_seconds": body.crossfade_seconds,
         "master_volume": body.master_volume,
         "eq": body.eq or {}}

    # ФИКС: есть трек на деке -> пользователь хочет играть -> playing.
    # Оба дека пусты -> это «Стоп» -> stopped.
    has_track = bool(d["deck_a"] or d["deck_b"])
    new_state = "playing" if has_track else "stopped"

    db.execute(text(
        "UPDATE music_zones SET dj_state=:d, desired_state=:s,"
        " updated_at=now() WHERE id=:z"),
        {"d": json.dumps(d, ensure_ascii=False), "s": new_state, "z": zid})
    db.commit()

    if zone["provider_type"] == "external":
        deps.push_external(zone, "dj_load", {"deck": "A", "track": d["deck_a"]})
        deps.push_external(zone, "dj_load", {"deck": "B", "track": d["deck_b"]})
        deps.push_external(zone, "dj_crossfade", {"active": d["active_deck"],
                                                  "seconds": d["crossfade_seconds"]})
        deps.push_external(zone, "dj_master", {"level": d["master_volume"]})
        deps.push_external(zone, "dj_eq", {"eq": d["eq"]})
    return {"ok": True, "zone": zid, "state": new_state, **d}