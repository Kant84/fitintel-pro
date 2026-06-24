# Исправляем prefix для reports_router
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_router = 'app.include_router(reports_router, prefix=settings.API_V1_PREFIX)'
new_router = 'app.include_router(reports_router, prefix=settings.API_V1_PREFIX + "/reports")'

if old_router in content:
    content = content.replace(old_router, new_router)
    with open('app/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Prefix исправлен!")
else:
    print("Не найдено подключение reports_router")
