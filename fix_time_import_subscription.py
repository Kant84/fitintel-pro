# fix_time_import_subscription.py
with open('app/schemas/subscription.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from datetime import date, datetime'''
new_import = '''from datetime import date, datetime, time'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/schemas/subscription.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт time добавлен в subscription.py!")
else:
    print("ERROR: Не найден импорт datetime")
