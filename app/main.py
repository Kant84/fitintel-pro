# app/main.py

from fastapi import FastAPI
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
from app.api.v1.wallet import router as wallet_router
from app.api.v1.payments import router as payments_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.cash_desk import router as cash_desk_router
from app.api.v1.sales import router as sales_router
from app.api.v1.devices import router as devices_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.selfservice import router as selfservice_router
from app.api.v1.documents import router as documents_router
from app.api.v1.marketing import router as marketing_router
from app.api.v1.gamification import router as gamification_router
from app.api.v1.online_training import router as online_training_router
from app.api.v1.hardware import router as hardware_router
from app.api.v1.chat import router as chat_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.yookassa import router as yookassa_router

# Face ID + License (v1.3.0)
from app.routers.face_id import router as face_id_router
from app.routers.license import router as license_router

# === APP ===
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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
app.include_router(wallet_router, prefix=settings.API_V1_PREFIX)
app.include_router(payments_router, prefix=settings.API_V1_PREFIX)
app.include_router(receipts_router, prefix=settings.API_V1_PREFIX)
app.include_router(cash_desk_router, prefix=settings.API_V1_PREFIX)
app.include_router(sales_router, prefix=settings.API_V1_PREFIX)
app.include_router(devices_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(selfservice_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(marketing_router, prefix=settings.API_V1_PREFIX)
app.include_router(gamification_router, prefix=settings.API_V1_PREFIX)
app.include_router(online_training_router, prefix=settings.API_V1_PREFIX)
app.include_router(hardware_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(telegram_router, prefix=settings.API_V1_PREFIX)
app.include_router(yookassa_router, prefix=settings.API_V1_PREFIX)
app.include_router(face_id_router, prefix=settings.API_V1_PREFIX)
app.include_router(license_router, prefix=settings.API_V1_PREFIX)

# === ROOT ===
@app.get("/")
async def root() -> dict[str, str]:
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "api_prefix": settings.API_V1_PREFIX,
    }
