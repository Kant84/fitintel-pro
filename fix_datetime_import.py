# fix_datetime_import.py
with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from datetime import timedelta'''

new_import = '''from datetime import timedelta, datetime'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт datetime добавлен!")
else:
    print("ERROR: Не найден импорт")
