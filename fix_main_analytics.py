# fix_main_analytics.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''from app.api.v1.lockers import router as lockers_router'''
new = '''from app.api.v1.lockers import router as lockers_router
from app.api.v1.analytics import router as analytics_router'''

if old in content:
    content = content.replace(old, new)
    
    old2 = '''app.include_router(lockers_router, prefix=settings.API_V1_PREFIX)'''
    new2 = '''app.include_router(lockers_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)'''
    
    if old2 in content:
        content = content.replace(old2, new2)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Router analytics подключен!")
    else:
        print("ERROR: Не найден include_router lockers")
else:
    print("ERROR: Не найден импорт lockers")
