# fix_engine.py
with open('app/db/base.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_engine = '''# engine = create_engine(DATABASE_URL)'''

new_engine = '''engine = create_engine(DATABASE_URL)'''

if old_engine in content:
    content = content.replace(old_engine, new_engine)
    with open('app/db/base.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("engine раскомментирован!")
else:
    print("ERROR: Не найден engine")
