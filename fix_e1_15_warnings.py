# fix_e1_15_warnings.py
with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Меняем 15 минут на 5 минут и добавляем предупреждения
old_block = '''            if user.failed_login_count >= 5:
                from datetime import datetime, timezone, timedelta
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                user.failed_login_count = 0
                self.db.commit()
                raise HTTPException(status_code=423, detail="Аккаунт заблокирован на 15 минут")
            self.db.commit()
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")'''

new_block = '''            remaining = 5 - user.failed_login_count
            if user.failed_login_count >= 5:
                from datetime import datetime, timezone, timedelta
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
                user.failed_login_count = 0
                self.db.commit()
                raise HTTPException(status_code=423, detail="Аккаунт заблокирован на 5 минут после 5 неудачных попыток")
            self.db.commit()
            raise HTTPException(status_code=401, detail=f"Неверный логин или пароль. Осталось попыток: {remaining}")'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Исправлено: таймер 5 минут + предупреждения о попытках!")
else:
    print("Не найден блок для замены. Проверьте файл.")
