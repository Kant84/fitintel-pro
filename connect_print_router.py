# connect_print_router.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт
old_import = 'from app.api.v1.reports import router as reports_router'
new_import = 'from app.api.v1.reports import router as reports_router\nfrom app.api.v1.print import router as print_router'

if old_import in content:
    content = content.replace(old_import, new_import)
    
    # Добавляем подключение
    old_router = 'app.include_router(reports_router, prefix=settings.API_V1_PREFIX + "/reports")'
    new_router = 'app.include_router(reports_router, prefix=settings.API_V1_PREFIX + "/reports")\napp.include_router(print_router, prefix=settings.API_V1_PREFIX + "/print")'
    
    if old_router in content:
        content = content.replace(old_router, new_router)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Print router подключен!")
    else:
        print("ERROR: Не найден reports_router")
else:
    print("ERROR: Не найден импорт reports")
