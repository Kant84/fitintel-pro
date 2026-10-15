#app\api\v1\music\playlists.py
# -*- coding: utf-8 -*-
"""Плейлисты: CRUD."""
import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_db
from . import deps

router = APIRouter()


class PlaylistIn(BaseModel):
    name: str
    description: str = ""
    tracks: list = []
    is_energize: bool = False


@router.get("/playlists")
def pl_list(db=Depends(get_db)):
    deps.ensure(db)
    return [deps.row(r) for r in db.execute(
        text("SELECT * FROM music_playlists ORDER BY name")).fetchall()]


@router.post("/playlists", status_code=201)
def pl_create(body: PlaylistIn, db=Depends(get_db)):
    deps.ensure(db)
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
    deps.ensure(db)
    db.execute(text("DELETE FROM music_playlists WHERE id=:p"), {"p": pid})
    db.commit()
    return None