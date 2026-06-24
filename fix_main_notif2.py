# fix_main_notifications.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Добавляем импорт
old_import = '''from app.api.v1.sse import router as sse_router'''
new_import = '''from app.api.v1.sse import router as sse_router
from app.api.v1.notifications import router as notifications_router'''

if old_import in content:
    content = content.replace(old_import, new_import)
    
    # 2. Добавляем include_router (после первого sse_router)
    old_include = '''app.include_router(sse_router, prefix=settings.API_V1_PREFIX)'''
    new_include = '''app.include_router(sse_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)'''
    
    # Заменяем только первое вхождение
    content = content.replace(old_include, new_include, 1)
    
    with open('app/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Notifications router подключен!")
else:
    print("ERROR: Не найден импорт sse_router")
