# fix_json_import.py
with open('app/models/credential.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from sqlalchemy import String, ForeignKey, Date, DateTime, Text'''
new_import = '''from sqlalchemy import String, ForeignKey, Date, DateTime, Text, JSON'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/models/credential.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт JSON добавлен!")
else:
    print("ERROR: Не найден импорт")
