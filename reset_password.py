"""Сброс пароля пользователя (локально, безопасно)"""
import sys
sys.path.insert(0, ".")

import app.main  # загружает все модели
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User

db = SessionLocal()

print("=== Пользователи в системе ===")
users = db.query(User).all()
for u in users:
    print(f"  логин: {u.username!r:30} роль: {getattr(u, 'role', '?')}  активен: {u.is_active}")

target = input("\nЛогин для сброса: ").strip()
new_pass = input("Новый пароль (мин. 8 символов): ").strip()

if len(new_pass) < 8:
    print("ОШИБКА: пароль короче 8 символов")
    raise SystemExit(1)

user = db.query(User).filter(User.username == target).first()
if not user:
    print(f"ОШИБКА: пользователь {target!r} не найден")
    raise SystemExit(1)

user.hashed_password = get_password_hash(new_pass)
user.is_active = True
db.commit()
print(f"OK: пароль для {target!r} изменён. Входите с новым паролем.")