# -*- coding: utf-8 -*-
"""Music API v3 — пакет. Собирает роутеры модулей под prefix="/music".
main.py подключает как раньше: from app.api.v1.music import router as music_router"""
from fastapi import APIRouter

from . import zones, playlists, schedule, dj, sfx, agent

router = APIRouter(prefix="/music")
router.include_router(zones.router)
router.include_router(playlists.router)
router.include_router(schedule.router)
router.include_router(dj.router)
router.include_router(sfx.router)
router.include_router(agent.router)