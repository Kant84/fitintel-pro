# app/main.py

# импорт FastAPI
from fastapi import FastAPI

# импорт настроек приложения
from app.core.config import settings

# импорт роутера auth
from app.api.v1.auth import router as auth_router

# импорт роутера users
from app.api.v1.users import router as users_router

from app.api.v1.roles import router as roles_router

from app.api.v1.permissions import router as permissions_router

from app.api.v1.auth_debug import router as auth_debug_router

from app.api.v1.rbac import router as rbac_router

# импорт роутера clients
from app.api.v1.clients import router as clients_router

# импорт роутера client_history
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


# создаём приложение FastAPI
app = FastAPI(
    # название приложения
    title=settings.APP_NAME,
    # режим отладки
    debug=settings.APP_DEBUG,
    # путь к Swagger UI
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    # путь к ReDoc
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    # путь к OpenAPI-схеме
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# подключаем auth router
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)

# подключаем users router
app.include_router(users_router, prefix=settings.API_V1_PREFIX)

# подключаем clients router
app.include_router(clients_router, prefix=settings.API_V1_PREFIX)

# подключаем client_history router
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

# временная отладка маршрутов — только после создания app
for route in app.routes:
    print(route.path, route.methods)


# корневой тестовый маршрут
@app.get("/")
async def root() -> dict[str, str]:
    """
    Простой тестовый маршрут, чтобы проверить,
    что приложение запускается и конфигурация подхватилась.
    """
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "api_prefix": settings.API_V1_PREFIX,
    }