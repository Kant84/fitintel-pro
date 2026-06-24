# fix_time_import.py
with open('app/schemas/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from datetime import datetime'''
new_import = '''from datetime import datetime, time'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/schemas/tariff.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт time добавлен!")
else:
    print("ERROR: Не найден импорт datetime")
