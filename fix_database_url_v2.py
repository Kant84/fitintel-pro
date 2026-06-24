# fix_database_url_v2.py
with open('app/db/base.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_url = '''DATABASE_URL = "postgresql+psycopg://fitnexus_user:FitNexus_User_2026!@127.0.0.1:5432/fitnexus"'''

new_url = '''DATABASE_URL = "postgresql+psycopg://postgres:FitNexus_Postgres_2026!@127.0.0.1:5432/fitnexus"'''

if old_url in content:
    content = content.replace(old_url, new_url)
    with open('app/db/base.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DATABASE_URL исправлен на правильный!")
else:
    print("ERROR: Не найден DATABASE_URL")
