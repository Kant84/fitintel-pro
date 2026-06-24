# fix_session_local.py
with open('app/db/base.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_session = '''# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)'''

new_session = '''SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)'''

if old_session in content:
    content = content.replace(old_session, new_session)
    with open('app/db/base.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SessionLocal раскомментирован!")
else:
    print("ERROR: Не найден SessionLocal")
