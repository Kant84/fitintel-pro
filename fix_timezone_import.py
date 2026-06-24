# fix_timezone_import.py
with open('app/services/credential_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from datetime import datetime, date, timedelta'''
new_import = '''from datetime import datetime, date, timedelta, timezone'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/services/credential_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт timezone добавлен!")
else:
    print("ERROR: Не найден импорт datetime")
