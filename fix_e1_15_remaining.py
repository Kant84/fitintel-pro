# fix_e1_15_remaining.py
with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем порядок: сначала проверяем блокировку, потом считаем remaining
old_logic = '''            # проверяем пароль
        if not verify_password(password, self.get_user_password_hash(user)):
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                from datetime import datetime, timezone, timedelta
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
                user.failed_login_count = 0
                self.db.commit()
                raise HTTPException(status_code=423, detail="Аккаунт заблокирован на 5 минут после 5 неудачных попыток")
            self.db.commit()
            raise HTTPException(status_code=401, detail=f"Неверный логин или пароль. Осталось попыток: {remaining}")'''

new_logic = '''            # проверяем пароль
        if not verify_password(password, self.get_user_password_hash(user)):
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                from datetime import datetime, timezone, timedelta
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
                user.failed_login_count = 0
                self.db.commit()
                raise HTTPException(status_code=423, detail="Аккаунт заблокирован на 5 минут после 5 неудачных попыток")
            self.db.commit()
            remaining = 5 - user.failed_login_count
            raise HTTPException(status_code=401, detail=f"Неверный логин или пароль. Осталось попыток: {remaining}")'''

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Исправлено! Теперь правильно: попытка 1 = 4 осталось, попытка 4 = 1 осталось, попытка 5 = блокировка")
else:
    print("Не найден блок для замены")
