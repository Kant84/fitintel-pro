#app\api\v1\music\__init__.py
# -*- coding: utf-8 -*-
"""Music API v3 — пакет. Собирает роутеры модулей под prefix="/music"."""
from fastapi import APIRouter

from . import zones, playlists, schedule, dj, sfx, agent, license

router = APIRouter(prefix="/music")
router.include_router(zones.router)
router.include_router(playlists.router)
router.include_router(schedule.router)
router.include_router(dj.router)
router.include_router(sfx.router)
router.include_router(agent.router)
router.include_router(license.router)