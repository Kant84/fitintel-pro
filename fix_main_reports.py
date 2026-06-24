# Добавляем импорт reports
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт после video_alerts
old_import = 'from app.api.v1.video_alerts import router as video_alerts_router'
new_import = 'from app.api.v1.video_alerts import router as video_alerts_router\nfrom app.api.v1.reports import router as reports_router'

if old_import in content:
    content = content.replace(old_import, new_import)
    
    # Добавляем подключение router
    old_router = 'app.include_router(video_alerts_router, prefix=settings.API_V1_PREFIX)'
    new_router = 'app.include_router(video_alerts_router, prefix=settings.API_V1_PREFIX)\napp.include_router(reports_router, prefix=settings.API_V1_PREFIX)'
    
    if old_router in content:
        content = content.replace(old_router, new_router)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("reports_router подключен!")
    else:
        print("Не найдено подключение video_alerts_router")
else:
    print("Не найден импорт video_alerts")
