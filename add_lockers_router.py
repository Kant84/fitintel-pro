# add_lockers_router.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from app.api.v1.hardware import router as hardware_router'''
new_import = '''from app.api.v1.hardware import router as hardware_router
from app.api.v1.lockers import router as lockers_router'''

if old_import in content:
    content = content.replace(old_import, new_import)
    
    # Добавляем include_router
    old_include = '''app.include_router(hardware_router, prefix=settings.API_V1_PREFIX)'''
    new_include = '''app.include_router(hardware_router, prefix=settings.API_V1_PREFIX)
app.include_router(lockers_router, prefix=settings.API_V1_PREFIX)'''
    
    if old_include in content:
        content = content.replace(old_include, new_include)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Router lockers подключен!")
    else:
        print("ERROR: Не найден include_router")
else:
    print("ERROR: Не найден импорт hardware_router")
