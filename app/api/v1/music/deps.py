#app\api\v1\music\deps.py
# -*- coding: utf-8 -*-
"""Общие зависимости музыкального модуля: хелперы и push на бокс провайдера."""
import datetime
import json
import threading
import urllib.request

from fastapi import HTTPException
from sqlalchemy import text

def ensure(db):
    """Схема создаётся Alembic-миграцией, а не конкурентно в HTTP-запросах."""
    return None


def row(r):
    return dict(r._mapping)


def get_zone(db, zid):
    ensure(db)
    r = db.execute(text("SELECT * FROM music_zones WHERE id=:z"), {"z": zid}).first()
    if not r:
        raise HTTPException(404, "зона не найдена")
    return row(r)


def cfg(zone):
    c = zone.get("provider_config") or {}
    return json.loads(c) if isinstance(c, str) else c


def dj_state(zone):
    c = zone.get("dj_state") or {}
    return json.loads(c) if isinstance(c, str) else c


def resolve_schedule(db, zone):
    """Если на «сейчас» есть правило расписания — применяет и сохраняет."""
    now = datetime.datetime.now()
    rules = db.execute(text(
        "SELECT * FROM music_schedule WHERE zone_id=:z AND (day_of_week=-1 OR day_of_week=:d)"
        " ORDER BY time_from"), {"z": zone["id"], "d": now.weekday()}).fetchall()
    cur = now.time()
    for r in rules:
        rule = row(r)
        if rule["time_from"] <= cur <= rule["time_to"]:
            if (zone["desired_state"] != "playing"
                    or zone["desired_playlist_id"] != rule["playlist_id"]
                    or zone["volume"] != rule["volume"]):
                db.execute(text(
                    "UPDATE music_zones SET desired_state='playing', desired_playlist_id=:p,"
                    " volume=:v, updated_at=now() WHERE id=:z"),
                    {"p": rule["playlist_id"], "v": rule["volume"], "z": zone["id"]})
                db.commit()
                zone.update(desired_state="playing",
                            desired_playlist_id=rule["playlist_id"],
                            volume=rule["volume"])
            return zone
    return zone


def push_external(zone, action, payload=None):
    """Пуш команды на бокс провайдера (в фоне, не блокирует ответ)."""
    c = cfg(zone)
    base = c.get("base_url")
    if not base:
        print("PUSH SKIP: нет base_url у зоны", zone["name"])
        return
    url = base.rstrip("/") + c.get("cmd_path", "/cmd")
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