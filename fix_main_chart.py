# fix_main_chart.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''from app.api.v1.notifications import router as notifications_router'''
new = '''from app.api.v1.notifications import router as notifications_router
from app.api.v1.analytics_chart import router as analytics_chart_router'''

if old in content:
    content = content.replace(old, new)
    
    old2 = '''app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)'''
    new2 = '''app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_chart_router, prefix=settings.API_V1_PREFIX)'''
    
    if old2 in content:
        content = content.replace(old2, new2)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Chart router подключен!")
    else:
        print("ERROR")
else:
    print("ERROR")
