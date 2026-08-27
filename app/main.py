# app/main.py
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import setup_logging
import logging

# === Logging (Linux-style: logs/app.log, logs/error.log, logs/access.log) ===
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.info("FitIntel Pro starting — logging initialized")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan, title=settings.APP_NAME, version=settings.APP_VERSION)

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
from app.api.v1.wallet import router as wallet_router
from app.api.v1.payments import router as payments_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.cash_desk import router as cash_desk_router
from app.api.v1.sales import router as sales_router
from app.api.v1.devices import router as devices_router
from app.api.v1.selfservice import router as selfservice_router
from app.api.v1.documents import router as documents_router
from app.api.v1.marketing import router as marketing_router
from app.api.v1.gamification import router as gamification_router
from app.api.v1.online_training import router as online_training_router
from app.api.v1.online_sessions import router as online_sessions_router
from app.api.v1.hardware import router as hardware_router
from app.api.v1.equipment import router as equipment_router
from app.api.v1.chat import router as chat_router
from app.api.v1.chats import router as chats_router, ws_router as chats_ws_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.max_bot import router as max_bot_router
from app.api.v1.yookassa import router as yookassa_router
from app.api.v1.client_verification import router as verify_router
from app.api.v1.setup import router as setup_router
from app.api.v1.endpoints.fiscal import fiscal_router
from app.api.v1.endpoints.accounting import accounting_router
from app.api.v1 import feature_flags
from app.api.v1.feature_flags import router as feature_flags_router
from app.api.v1.services import router as services_router
from app.api.v1.dynamic_qr import router as dynamic_qr_router
from app.api.v1.face_id import router as face_id_router
from app.api.v1.video_alerts import router as video_alerts_router
from app.api.v1.reports import router as reports_router
from app.api.v1.print import router as print_router
from app.api.v1.trainers import router as trainers_router
from app.api.v1.warehouse import router as warehouse_router
from app.api.v1.commercial import router as commercial_router
from app.api.v1.exports import router as exports_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.ws_alerts import router as ws_alerts_router
from app.api.v1.phone_verify import router as phone_verify_router
from app.api.v1.fiscal import router as fiscal_e31_router
from app.api.v1.documents import router as documents_e33_router
from app.api.v1.selfservice import e35_router as selfservice_e35_router
from app.api.v1.recurring import router as recurring_router
from app.api.v1.referrals import router as referrals_router
from app.api.v1.corporate import router as corporate_router
from app.api.v1.seasonal import router as seasonal_router
from app.api.v1.niche import router as niche_router
from app.api.v1.booking_widget import router as booking_widget_router
from app.api.v1.documents_bulk import router as documents_bulk_router
from app.api.v1.feature_flags_adv import router as feature_flags_adv_router
from app.api.v1.analytics_ai import router as analytics_ai_router
from app.api.v1.video_ai import router as video_ai_router
from app.api.v1.max_bot_fsm import router as max_bot_fsm_router
from app.api.v1.dal import router as dal_router
from app.api.v1.reporting import router as reporting_router
from app.api.v1.ops import router as ops_router
from app.api.v1.ui_config import router as ui_config_router
from app.routers.license import router as license_router

# === ROUTES ===
app.include_router(dynamic_qr_router, prefix=settings.API_V1_PREFIX)
app.include_router(face_id_router, prefix=settings.API_V1_PREFIX)
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
app.include_router(selfservice_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_bulk_router, prefix="/api/v1")
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(marketing_router, prefix=settings.API_V1_PREFIX)
app.include_router(gamification_router, prefix=settings.API_V1_PREFIX)
app.include_router(online_training_router, prefix=settings.API_V1_PREFIX)
app.include_router(online_sessions_router, prefix=settings.API_V1_PREFIX)
app.include_router(hardware_router, prefix=settings.API_V1_PREFIX)
app.include_router(equipment_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(chats_router, prefix=settings.API_V1_PREFIX)
app.include_router(chats_ws_router)
app.include_router(telegram_router, prefix=settings.API_V1_PREFIX)
app.include_router(max_bot_router, prefix=settings.API_V1_PREFIX)
app.include_router(yookassa_router, prefix=settings.API_V1_PREFIX)
app.include_router(license_router)
app.include_router(verify_router, prefix=settings.API_V1_PREFIX)
app.include_router(setup_router, prefix=settings.API_V1_PREFIX)
app.include_router(fiscal_router, prefix=settings.API_V1_PREFIX)
app.include_router(accounting_router, prefix=settings.API_V1_PREFIX)
app.include_router(services_router, prefix=settings.API_V1_PREFIX)
app.include_router(dynamic_qr_router, prefix=settings.API_V1_PREFIX)
app.include_router(video_alerts_router, prefix=settings.API_V1_PREFIX)
app.include_router(feature_flags_adv_router, prefix="/api/v1")
app.include_router(feature_flags_router, prefix=settings.API_V1_PREFIX + "/feature-flags")
app.include_router(reports_router, prefix=settings.API_V1_PREFIX + "/reports")
app.include_router(print_router, prefix=settings.API_V1_PREFIX + "/print")
app.include_router(trainers_router, prefix=settings.API_V1_PREFIX)
app.include_router(warehouse_router, prefix=settings.API_V1_PREFIX)
app.include_router(commercial_router, prefix=settings.API_V1_PREFIX)
app.include_router(exports_router, prefix=settings.API_V1_PREFIX)
app.include_router(integrations_router, prefix=settings.API_V1_PREFIX)
app.include_router(ws_alerts_router, prefix="/ws")
app.include_router(phone_verify_router, prefix="/api/v1")
app.include_router(fiscal_e31_router, prefix="/api/v1")
app.include_router(documents_e33_router, prefix="/api/v1")
app.include_router(selfservice_e35_router, prefix="/api/v1")
app.include_router(recurring_router, prefix="/api/v1")
app.include_router(referrals_router, prefix="/api/v1")
app.include_router(corporate_router, prefix="/api/v1")
app.include_router(seasonal_router, prefix="/api/v1")
app.include_router(niche_router, prefix="/api/v1")
app.include_router(booking_widget_router, prefix="/api/v1")
app.include_router(analytics_ai_router, prefix="/api/v1")
app.include_router(video_ai_router, prefix="/api/v1")
app.include_router(max_bot_fsm_router, prefix="/api/v1")
app.include_router(dal_router, prefix="/api/v1")
app.include_router(reporting_router, prefix="/api/v1")
app.include_router(ops_router, prefix="/api/v1")
app.include_router(ui_config_router, prefix=settings.API_V1_PREFIX)

from app.api.v1 import integrations_config as _e56_ic
from app.api.v1 import messenger as _e56_msg
app.include_router(_e56_ic.router, prefix="/api/v1")
app.include_router(_e56_msg.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "FitIntel AI API", "version": settings.APP_VERSION, "docs": "/docs"}

# === E59B: document templates router ===
try:
    from app.api.v1.document_templates import router as doc_templates_router
    app.include_router(doc_templates_router, prefix="/api/v1/document-templates", tags=["document-templates"])
    print("document_templates router OK")
except Exception as e:
    print("document_templates router FAIL:", e)


# === E22-lite: self-learning AI router ===
try:
    from app.api.v1.ai_engine import router as ai_router
    app.include_router(ai_router, prefix="/api/v1", tags=["ai"])
    print("ai router OK")
except Exception as e:
    print("ai router FAIL:", e)


# === License validation ===
try:
    from app.api.v1.license_api import router as license_router
    app.include_router(license_router, prefix="/api/v1", tags=["license"])
    print("license router OK")
except Exception as e:
    print("license router FAIL:", e)


# === E66: license limit middleware ===
try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import JSONResponse

    class LicenseLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            try:
                path = request.url.path.rstrip("/")
                if request.method == "POST" and (path.endswith("/clients") or path.endswith("/members")):
                    from app.api.v1.license_api import license_block_check
                    chk = license_block_check()
                    if chk.get("block"):
                        return JSONResponse(
                            {"detail": "Лимит клиентов по лицензии исчерпан (%s/%s). Обновите тариф." % (chk.get("used"), chk.get("limit"))},
                            status_code=403)
                    if chk.get("over_limit"):
                        print("LICENSE WARNING: клиентов больше лимита (мягкий режим)")
            except Exception as e:
                print("license middleware:", e)
            return await call_next(request)

    app.add_middleware(LicenseLimitMiddleware)
    print("license middleware OK")
except Exception as e:
    print("license middleware FAIL:", e)


# === E66_ROUTE_PRIORITY v4: работа с _IncludedRouter (ленивая маршрутизация) ===
def _e66_fix_license_routes():
    try:
        from app.api.v1 import license_api as _la
        our_eps = {id(getattr(x, "endpoint", None)) for x in _la.router.routes}
        our_short = {"/license/validate", "/license/limits", "/license/activate",
                     "/license/current", "/license/mode"}

        def inner(r):
            v = getattr(r, "routes", None)
            if v:
                return list(v)
            return list(getattr(getattr(r, "router", None), "routes", []) or [])

        entries = list(app.router.routes)
        ours_idx = None
        for i, r in enumerate(entries):
            if {id(getattr(x, "endpoint", None)) for x in inner(r)} & our_eps:
                ours_idx = i
                break
        if ours_idx is None:
            app.include_router(_la.router, prefix="/api/v1")
            entries = list(app.router.routes)
            for i, r in enumerate(entries):
                if {id(getattr(x, "endpoint", None)) for x in inner(r)} & our_eps:
                    ours_idx = i
                    break
            print(f"[E66] принудительно включён, ours_idx={ours_idx}")

        dropped = 0
        for i, r in enumerate(entries):
            if i == ours_idx:
                continue
            ir = getattr(r, "router", None)
            target = ir if (ir is not None and hasattr(ir, "routes")) else (r if hasattr(r, "routes") else None)
            if target is None:
                continue
            kept = []
            for x in list(target.routes):
                pth = getattr(x, "path", "") or ""
                short = pth[len("/api/v1"):] if pth.startswith("/api/v1") else pth
                if short in our_short:
                    dropped += 1
                    continue
                kept.append(x)
            if len(kept) != len(target.routes):
                target.routes[:] = kept

        if ours_idx is not None and ours_idx > 4:
            e = entries.pop(ours_idx)
            entries.insert(4, e)
            app.router.routes[:] = entries
        print(f"[E66] готово: ours_idx={ours_idx}, вырезано конфликтов={dropped}")
    except Exception as e:
        print(f"[E66] WARN: {type(e).__name__}: {e}")

_e66_fix_license_routes()


# === E17: notifications ===
try:
    from app.api.v1.notifications import router as notifications_router, _ensure as _n17_ensure
    app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])
    _n17_ensure()
    print("notifications router OK")
except Exception as e:
    print("notifications router FAIL:", e)


# === E18_COMMERCE_ROUTER ===
try:
    from app.api.v1.branding import router as branding_router, _ensure as _e18_ensure
    app.include_router(branding_router, prefix="/api/v1", tags=["commerce"])
    _e18_ensure()
    print("E18 commerce router OK")
except Exception as _e18e:
    print("E18 commerce router FAIL:", _e18e)


# === E19_EXPORT_ROUTER ===
try:
    from app.api.v1.export_api import router as export_router
    app.include_router(export_router, prefix="/api/v1", tags=["export"])
    print("E19 export router OK")
except Exception as _e19e:
    print("E19 export router FAIL:", _e19e)




# === E21_AA_BRIDGE: интеграция с A&A ===
try:
    from app.api.v1.aa_bridge import router as aa_router
    app.include_router(aa_router, prefix="/api/v1", tags=["integrations"])
    print("E21 A&A bridge OK")
except Exception as _e21:
    print("E21 A&A bridge FAIL:", _e21)


# === E7_BACKUP_SCHEDULER: автобэкап PostgreSQL 03:00 ===
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from scripts.backup_postgres import backup, rotate
    _sched = BackgroundScheduler()
    _sched.add_job(lambda: backup() and rotate(), "cron", hour=3, minute=0, id="pg_backup")
    _sched.start()
    print("E7 backup scheduler OK (03:00 daily)")
except Exception as _e7:
    print("E7 backup scheduler FAIL:", _e7)


# === RFID Reader API ===
try:
    from app.api.v1.reader import router as reader_router
    app.include_router(reader_router, prefix="/api/v1")
    print("RFID reader API OK")
except Exception as _er:
    print("RFID reader API FAIL:", _er)


# === E15-SKUD: ITCService integration ===
try:
    from app.api.v1.skud_itconnect import router as skud_router
    app.include_router(skud_router, prefix="/api/v1")
    print("E15-SKUD OK")
except Exception as _eskud:
    print("E15-SKUD FAIL:", _eskud)


# === E60: Auto-Scheduler API ===
try:
    from app.api.v1.auto import router as auto_router
    app.include_router(auto_router, prefix="/api/v1")
    print("E60 Auto-Scheduler OK")
except Exception as _eauto:
    print("E60 Auto-Scheduler FAIL:", _eauto)


# === E60: Self-Learning API ===
try:
    from app.api.v1.self_learning import router as sl_router
    app.include_router(sl_router, prefix="/api/v1")
    print("E60 Self-Learning OK")
except Exception as _esl:
    print("E60 Self-Learning FAIL:", _esl)
