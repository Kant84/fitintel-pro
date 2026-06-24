# fix_get_db.py
with open('app/db/base.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_get_db = '''def get_db():
    # db = SessionLocal()
    try:
        # yield db
        pass
    finally:
        # db.close()
        pass'''

new_get_db = '''def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()'''

if old_get_db in content:
    content = content.replace(old_get_db, new_get_db)
    with open('app/db/base.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("get_db исправлен!")
else:
    print("ERROR: Не найден get_db")
