# fix_main_scheduler2.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт
old_import = '''from app.api.v1.analytics_dashboard import router as analytics_dashboard_router'''
new_import = '''from app.api.v1.analytics_dashboard import router as analytics_dashboard_router
from app.services.scheduler_service import start_analytics_scheduler, shutdown_analytics_scheduler
from contextlib import asynccontextmanager'''

if old_import in content:
    content = content.replace(old_import, new_import)
    
    # Добавляем lifespan перед app = FastAPI
    old_app = '''app = FastAPI('''
    new_app = '''@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_analytics_scheduler()
    yield
    # Shutdown
    shutdown_analytics_scheduler()

app = FastAPI(lifespan=lifespan,'''
    
    if old_app in content:
        content = content.replace(old_app, new_app)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Scheduler + lifespan добавлен!")
    else:
        print("ERROR: Не найден app = FastAPI")
else:
    print("ERROR: Не найден импорт dashboard")
