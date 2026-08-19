from fastapi import APIRouter
from app.api.v1 import services, auth, users, exports, analytics, devices, dynamic_qr

router = APIRouter()

router.include_router(services.router, tags=["Services"])
router.include_router(auth.router, tags=["Auth"])
router.include_router(users.router, tags=["Users"])
router.include_router(exports.router, tags=["Exports"])
router.include_router(analytics.router, tags=["Analytics"])
router.include_router(devices.router, tags=["Devices"])
router.include_router(dynamic_qr.router, tags=["Dynamic QR"])
