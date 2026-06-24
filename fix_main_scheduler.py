# fix_main_scheduler.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт
old_import = '''from app.api.v1.analytics_dashboard import router as analytics_dashboard_router'''
new_import = '''from app.api.v1.analytics_dashboard import router as analytics_dashboard_router
from app.services.scheduler_service import start_analytics_scheduler, shutdown_analytics_scheduler'''

if old_import in content:
    content = content.replace(old_import, new_import)
    
    # Добавляем запуск в startup
    old_startup = '''    print(f"Docs: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")'''
    new_startup = '''    print(f"Docs: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    
    # Запускаем планировщик аналитики (TS-012)
    start_analytics_scheduler()'''
    
    if old_startup in content:
        content = content.replace(old_startup, new_startup)
        
        # Добавляем shutdown
        old_shutdown = '''if __name__ == "__main__":'''
        new_shutdown = '''@app.on_event("shutdown")
def shutdown_event():
    shutdown_analytics_scheduler()

if __name__ == "__main__":'''
        
        if old_shutdown in content:
            content = content.replace(old_shutdown, new_shutdown)
            with open('app/main.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Scheduler подключен!")
        else:
            print("ERROR: Не найден __main__")
    else:
        print("ERROR: Не найден startup")
else:
    print("ERROR: Не найден импорт dashboard")
