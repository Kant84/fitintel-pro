# fix_import_locker_session.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''        from app.models.locker import Locker, LockerSession
        from app.models.locker_privilege import LockerPrivilege'''
new_import = '''        from app.models.locker import Locker
        from app.models.locker_session import LockerSession
        from app.models.locker_privilege import LockerPrivilege'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт LockerSession исправлен!")
else:
    print("ERROR: Не найден импорт")
