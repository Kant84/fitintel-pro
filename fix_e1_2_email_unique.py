# fix_e1_2_email_unique.py
# Исправление: добавление проверки уникальности email в auth_service.py

import re

# Читаем файл
with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем место для вставки (после проверки username)
old_code = '''        # проверяем уникальность username
        existing = self.db.query(User).filter(User.username == login).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")'''

new_code = '''        # проверяем уникальность username
        existing = self.db.query(User).filter(User.username == login).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")
        
        # проверяем уникальность email (если передан)
        if email:
            existing_email = self.db.query(User).filter(User.email == email).first()
            if existing_email:
                raise HTTPException(status_code=409, detail="Email already exists")'''

# Заменяем
if old_code in content:
    content = content.replace(old_code, new_code)
    
    # Сохраняем
    with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Исправление применено!")
    print("Проверка уникальности email добавлена в create_user()")
else:
    print("Не найдено место для вставки. Проверьте файл вручную.")
