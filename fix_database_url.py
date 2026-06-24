# fix_database_url.py
with open('app/db/base.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_url = '''# DATABASE_URL = "postgresql+psycopg://fitnexus_user:FitNexus_User_2026!@127.0.0.1:5433/fitnexus_ai"'''

new_url = '''DATABASE_URL = "postgresql+psycopg://fitnexus_user:FitNexus_User_2026!@127.0.0.1:5433/fitnexus_ai"'''

if old_url in content:
    content = content.replace(old_url, new_url)
    with open('app/db/base.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DATABASE_URL раскомментирован!")
else:
    print("ERROR: Не найден DATABASE_URL")
