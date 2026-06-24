# app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# === ROUTERS ===
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.permissions import router as permissions_router
from app.api.v1.auth_debug import router as auth_debug_router
from app.api.v1.rbac import router as rbac_router
from app.api.v1.clients import router as clients_router
from app.api.v1.client_history import router as client_history_router
from app.api.v1.tariffs import router as tariffs_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.health import router as health_router
from app.api.v1.subscription_lifecycle import router as subscription_lifecycle_router
from app.api.v1.visits import router as visits_router
from app.api.v1.access import router as access_router
from app.api.v1.credentials import router as credentials_router
from app.api.v1.access_cache import router as access_cache_router
from app.api.v1.lockers import router as lockers_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.sse import router as sse_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.analytics_chart import router as analytics_chart_router
from app.api.v1.analytics_dashboard import router as analytics_dashboard_router
from app.services.scheduler_service import start_analytics_scheduler, shutdown_analytics_scheduler
from contextlib import asynccontextmanager
from app.api.v1.wallet import router as wallet_router
from app.api.v1.payments import router as payments_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.cash_desk import router as cash_desk_router
from app.api.v1.sales import router as sales_router
from app.api.v1.devices import router as devices_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.sse import router as sse_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.analytics_chart import router as analytics_chart_router
from app.api.v1.analytics_dashboard import router as analytics_dashboard_router
from app.services.scheduler_service import start_analytics_scheduler, shutdown_analytics_scheduler
from contextlib import asynccontextmanager
from app.api.v1.selfservice import router as selfservice_router
from app.api.v1.documents import router as documents_router
from app.api.v1.marketing import router as marketing_router
from app.api.v1.gamification import router as gamification_router
from app.api.v1.online_training import router as online_training_router
from app.api.v1.hardware import router as hardware_router
from app.api.v1.lockers import router as lockers_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.sse import router as sse_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.analytics_chart import router as analytics_chart_router
from app.api.v1.analytics_dashboard import router as analytics_dashboard_router
from app.services.scheduler_service import start_analytics_scheduler, shutdown_analytics_scheduler
from contextlib import asynccontextmanager
from app.api.v1.chat import router as chat_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.yookassa import router as yookassa_router
from app.api.v1.client_verification import router as verify_router
from app.api.v1.setup import router as setup_router

from app.api.v1.endpoints.fiscal import fiscal_router
from app.api.v1.endpoints.accounting import accounting_router

from app.api.v1.endpoints.fiscal import fiscal_router
from app.api.v1.endpoints.accounting import accounting_router

# Face ID + License (v1.3.1)
from app.routers.face_id import router as face_id_router
from app.routers.license import router as license_router
from app.api.v1 import feature_flags  # E7a — Feature Flags
from app.api.v1.feature_flags import router as feature_flags_router
# Setup Wizard + License Guard (v1.3.1)
from app.middleware.license_middleware import LicenseMiddleware
# New routers for TZ v3.5
from app.api.v1.services import router as services_router
from app.api.v1.dynamic_qr import router as dynamic_qr_router
from app.api.v1.video_alerts import router as video_alerts_router
from app.api.v1.reports import router as reports_router
from app.api.v1.print import router as print_router
from app.api.v1.trainers import router as trainers_router
from app.api.v1.warehouse import router as warehouse_router
# === APP ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: инициализация Hardware Manager
    from app.hardware.manager import DeviceManager
    acs_config = {
        "device_id": "acs_reader_main",
        "driver_class": "AcsAcr1252uDriver",
        "reader_name": "ACS ACR1252 1S CL Reader PICC 0",
    }
    await DeviceManager.add_device(acs_config)
    print("[HW] ACS ACR1252U initialized")
    
    # Startup: планировщик аналитики
    start_analytics_scheduler()
    
    yield
    
    # Shutdown: планировщик аналитики
    shutdown_analytics_scheduler()
    
    # Shutdown: отключение устройств
    for device_id in list(DeviceManager._devices.keys()):
        await DeviceManager.remove_device(device_id)
    print("[HW] All devices disconnected")

app = FastAPI(lifespan=lifespan,
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)
app.mount("/static/trainer-pwa", StaticFiles(directory="app/static/trainer-pwa"), name="trainer-pwa")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# === LICENSE MIDDLEWARE (blocks API without valid license) ===
# Excluded: setup, license, docs, health endpoints
app.add_middleware(LicenseMiddleware)

# === ROUTES ===
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(clients_router, prefix=settings.API_V1_PREFIX)
app.include_router(client_history_router, prefix=settings.API_V1_PREFIX)
app.include_router(roles_router, prefix=settings.API_V1_PREFIX)
app.include_router(permissions_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_debug_router, prefix=settings.API_V1_PREFIX)
app.include_router(rbac_router, prefix=settings.API_V1_PREFIX)
app.include_router(tariffs_router, prefix=settings.API_V1_PREFIX)
app.include_router(subscriptions_router, prefix=settings.API_V1_PREFIX)
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(subscription_lifecycle_router, prefix=settings.API_V1_PREFIX)
app.include_router(visits_router, prefix=settings.API_V1_PREFIX)
app.include_router(access_router, prefix=settings.API_V1_PREFIX)
app.include_router(credentials_router, prefix=settings.API_V1_PREFIX)
app.include_router(access_cache_router, prefix=settings.API_V1_PREFIX)
app.include_router(lockers_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(sse_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_chart_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(wallet_router, prefix=settings.API_V1_PREFIX)
app.include_router(payments_router, prefix=settings.API_V1_PREFIX)
app.include_router(receipts_router, prefix=settings.API_V1_PREFIX)
app.include_router(cash_desk_router, prefix=settings.API_V1_PREFIX)
app.include_router(sales_router, prefix=settings.API_V1_PREFIX)
app.include_router(devices_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(sse_router, prefix=settings.API_V1_PREFIX)
app.include_router(selfservice_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(marketing_router, prefix=settings.API_V1_PREFIX)
app.include_router(gamification_router, prefix=settings.API_V1_PREFIX)
app.include_router(online_training_router, prefix=settings.API_V1_PREFIX)
app.include_router(hardware_router, prefix=settings.API_V1_PREFIX)
app.include_router(lockers_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(sse_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(telegram_router, prefix=settings.API_V1_PREFIX)
app.include_router(yookassa_router, prefix=settings.API_V1_PREFIX)
app.include_router(face_id_router, prefix=settings.API_V1_PREFIX)
app.include_router(license_router)
app.include_router(verify_router, prefix=settings.API_V1_PREFIX)
app.include_router(setup_router, prefix=settings.API_V1_PREFIX)

app.include_router(fiscal_router, prefix=settings.API_V1_PREFIX)
app.include_router(accounting_router, prefix=settings.API_V1_PREFIX)

app.include_router(fiscal_router, prefix=settings.API_V1_PREFIX)
app.include_router(accounting_router, prefix=settings.API_V1_PREFIX)
# === ADD THESE ROUTES (after existing routes) ===
app.include_router(services_router, prefix=settings.API_V1_PREFIX)
app.include_router(dynamic_qr_router, prefix=settings.API_V1_PREFIX)
app.include_router(video_alerts_router, prefix=settings.API_V1_PREFIX)
app.include_router(feature_flags_router, prefix=settings.API_V1_PREFIX + "/feature-flags")
app.include_router(reports_router, prefix=settings.API_V1_PREFIX + "/reports")
app.include_router(print_router, prefix=settings.API_V1_PREFIX + "/print")
app.include_router(trainers_router, prefix=settings.API_V1_PREFIX)
app.include_router(warehouse_router, prefix=settings.API_V1_PREFIX)
# === ROOT ===
@app.get("/")
async def root():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "api_prefix": settings.API_V1_PREFIX,
        "license_required": True,
        "setup_url": f"{settings.API_V1_PREFIX}/setup",
    }
