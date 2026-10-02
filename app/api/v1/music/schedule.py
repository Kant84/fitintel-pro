# -*- coding: utf-8 -*-
"""Расписание автоматического воспроизведения по зонам."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.session import get_db
from . import deps

router = APIRouter()


class ScheduleIn(BaseModel):
    zone_id: str
    day_of_week: int = -1            # -1 = каждый день, 0=Пн .. 6=Вс
    time_from: str                   # "HH:MM"
    time_to: str
    playlist_id: str | None = None
    volume: int = Field(50, ge=0, le=100)


@router.get("/schedule")
def sched_list(zone_id: str | None = None, db=Depends(get_db)):
    deps.ensure(db)
    if zone_id:
        rows = db.execute(text(
            "SELECT * FROM music_schedule WHERE zone_id=:z"
            " ORDER BY day_of_week, time_from"), {"z": zone_id}).fetchall()
    else:
        rows = db.execute(text(
            "SELECT * FROM music_schedule ORDER BY zone_id, day_of_week, time_from")).fetchall()
    return [deps.row(r) for r in rows]


@router.post("/schedule", status_code=201)
def sched_add(body: ScheduleIn, db=Depends(get_db)):
    deps.ensure(db)
    deps.get_zone(db, body.zone_id)
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
    deps.ensure(db)
    db.execute(text("DELETE FROM music_schedule WHERE id=:i"), {"i": sid})
    db.commit()
    return None