"""Разблокировка + сброс пароля"""
import sys
sys.path.insert(0, ".")

import app.main
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User

db = SessionLocal()

target = input("Логин: ").strip()
new_pass = input("Новый пароль (мин. 8 символов): ").strip()

if len(new_pass) < 8:
    print("ОШИБКА: короче 8 символов"); raise SystemExit(1)

user = db.query(User).filter(User.username == target).first()
if not user:
    print("Пользователь не найден"); raise SystemExit(1)

user.hashed_password = get_password_hash(new_pass)
user.is_active = True
user.failed_login_count = 0
user.locked_until = None          # ← снимаем блокировку
db.commit()
print(f"OK: {target!r} разблокирован, пароль изменён. Входите сразу.")