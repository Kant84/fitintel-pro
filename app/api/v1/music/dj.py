# -*- coding: utf-8 -*-
"""DJ-пульт: состояние деков A/B, кроссфейд, мастер-громкость.
local_agent — применяет DJ-агент; external — пуш на бокс провайдера."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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
         "master_volume": body.master_volume}
    import json
    from sqlalchemy import text
    db.execute(text("UPDATE music_zones SET dj_state=:d, updated_at=now() WHERE id=:z"),
               {"d": json.dumps(d, ensure_ascii=False), "z": zid})
    db.commit()
    if zone["provider_type"] == "external":
        # Контракт для бокса провайдера: dj_load / dj_crossfade / dj_master.
        # Реальный формат команд подгоним под конкретную коробку (provider_config).
        deps.push_external(zone, "dj_load", {"deck": "A", "track": d["deck_a"]})
        deps.push_external(zone, "dj_load", {"deck": "B", "track": d["deck_b"]})
        deps.push_external(zone, "dj_crossfade", {"active": d["active_deck"],
                                                  "seconds": d["crossfade_seconds"]})
        deps.push_external(zone, "dj_master", {"level": d["master_volume"]})
    return {"ok": True, "zone": zid, **d}