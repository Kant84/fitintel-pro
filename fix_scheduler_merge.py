# fix_scheduler_merge.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем дублирующий lifespan
old = '''@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_analytics_scheduler()
    yield
    # Shutdown
    shutdown_analytics_scheduler()

app = FastAPI(lifespan=lifespan,
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)'''

new = '''app = FastAPI(lifespan=lifespan,
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)'''

if old in content:
    content = content.replace(old, new)
    
    # Добавляем scheduler в существующий lifespan
    old_yield = '''    yield
    
    # Shutdown: отключение устройств'''
    new_yield = '''    # Startup: планировщик аналитики
    start_analytics_scheduler()
    
    yield
    
    # Shutdown: планировщик аналитики
    shutdown_analytics_scheduler()
    
    # Shutdown: отключение устройств'''
    
    if old_yield in content:
        content = content.replace(old_yield, new_yield)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Scheduler объединён с существующим lifespan!")
    else:
        print("ERROR: Не найден yield в lifespan")
else:
    print("ERROR: Не найден дублирующий lifespan")
