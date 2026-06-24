# fix_database_port.py
with open('app/db/base.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_port = '''DATABASE_URL = "postgresql+psycopg://fitnexus_user:FitNexus_User_2026!@127.0.0.1:5433/fitnexus_ai"'''

new_port = '''DATABASE_URL = "postgresql+psycopg://fitnexus_user:FitNexus_User_2026!@127.0.0.1:5432/fitnexus"'''

if old_port in content:
    content = content.replace(old_port, new_port)
    with open('app/db/base.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DATABASE_URL исправлен на порт 5432!")
else:
    print("ERROR: Не найден DATABASE_URL")
