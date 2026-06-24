# fix_locker_service_import.py
with open('app/services/locker_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from app.models.locker import Locker, LockerSession'''
new_import = '''from app.models.locker import Locker
from app.models.locker_session import LockerSession'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/services/locker_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт LockerSession исправлен!")
else:
    print("ERROR: Не найден импорт")
