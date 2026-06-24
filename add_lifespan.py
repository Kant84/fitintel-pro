# add_lifespan.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Найдём импорт FastAPI и добавим lifespan
old_fastapi = '''from fastapi import FastAPI'''

new_fastapi = '''from fastapi import FastAPI
from contextlib import asynccontextmanager'''

if old_fastapi in content:
    content = content.replace(old_fastapi, new_fastapi)
    
    # Найдём создание app и добавим lifespan
    old_app = '''app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)'''

    new_app = '''@asynccontextmanager
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
    
    yield
    
    # Shutdown: отключение устройств
    for device_id in list(DeviceManager._devices.keys()):
        await DeviceManager.remove_device(device_id)
    print("[HW] All devices disconnected")

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)'''

    if old_app in content:
        content = content.replace(old_app, new_app)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Lifespan добавлен!")
    else:
        print("ERROR: Не найдено создание app")
else:
    print("ERROR: Не найден импорт FastAPI")
