# -*- coding: utf-8 -*-
"""Сэмплер: библиотека сэмплов + кнопки падов (очередь событий / пуш на бокс)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.session import get_db
from . import deps

router = APIRouter()


class SfxIn(BaseModel):
    name: str
    path: str
    volume: int = Field(80, ge=0, le=100)
    sort: int = 0


class PadFireIn(BaseModel):
    sfx_id: str


@router.get("/sfx")
def sfx_list(db=Depends(get_db)):
    deps.ensure(db)
    return [deps.row(r) for r in db.execute(
        text("SELECT * FROM music_sfx ORDER BY sort, name")).fetchall()]


@router.post("/sfx", status_code=201)
def sfx_create(body: SfxIn, db=Depends(get_db)):
    deps.ensure(db)
    sid = str(uuid.uuid4())
    db.execute(text("INSERT INTO music_sfx (id,name,path,volume,sort) VALUES (:i,:n,:p,:v,:s)"),
               {"i": sid, "n": body.name, "p": body.path, "v": body.volume, "s": body.sort})
    db.commit()
    return {"id": sid}


@router.delete("/sfx/{sid}", status_code=204)
def sfx_delete(sid: str, db=Depends(get_db)):
    deps.ensure(db)
    db.execute(text("DELETE FROM music_sfx WHERE id=:i"), {"i": sid})
    db.commit()
    return None


@router.post("/zones/{zid}/pad-fire")
def pad_fire(zid: str, body: PadFireIn, db=Depends(get_db)):
    """Один-шот сэмпл: событие в очередь (local) или пуш на бокс (external)."""
    zone = deps.get_zone(db, zid)
    r = db.execute(text("SELECT * FROM music_sfx WHERE id=:i"), {"i": body.sfx_id}).first()
    if not r:
        raise HTTPException(404, "сэмпл не найден")
    sfx = deps.row(r)
    if zone["provider_type"] == "external":
        deps.push_external(zone, "pad_fire",
                           {"sfx": {"name": sfx["name"], "path": sfx["path"],
                                    "volume": sfx["volume"]}})
        return {"ok": True, "zone": zid, "sfx": sfx["name"], "mode": "external"}
    eid = str(uuid.uuid4())
    db.execute(text("INSERT INTO music_pad_events (id,zone_id,sfx_id) VALUES (:i,:z,:s)"),
               {"i": eid, "z": zid, "s": body.sfx_id})
    db.commit()
    return {"ok": True, "event_id": eid, "zone": zid, "sfx": sfx["name"]}