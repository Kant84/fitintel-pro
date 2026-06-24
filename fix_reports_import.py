# Исправляем импорты в reports.py
with open('app/api/v1/reports.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = 'from app.api.deps import get_db, require_permission'
new_import = 'from app.api.dependencies import require_permission\nfrom app.db.session import get_db'

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/api/v1/reports.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорты исправлены!")
else:
    print("Не найден старый импорт")
