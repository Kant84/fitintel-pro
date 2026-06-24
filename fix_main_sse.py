# fix_main_sse.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''from app.api.v1.analytics import router as analytics_router'''
new = '''from app.api.v1.analytics import router as analytics_router
from app.api.v1.sse import router as sse_router'''

if old in content:
    content = content.replace(old, new)
    
    old2 = '''app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)'''
    new2 = '''app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(sse_router, prefix=settings.API_V1_PREFIX)'''
    
    if old2 in content:
        content = content.replace(old2, new2)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("SSE router подключен!")
    else:
        print("ERROR: Не найден include_router analytics")
else:
    print("ERROR: Не найден импорт analytics")
