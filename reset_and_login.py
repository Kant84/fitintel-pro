"""Сброс пароля + немедленная проверка входа — за один запуск"""
import sys
sys.path.insert(0, ".")
import app.main
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.services.auth_service import AuthService
from app.models.user import User

LOGIN = "my_new_username"
NEW_PASSWORD = "gfhjkmas"   # тот, что вы хотите

db = SessionLocal()
user = db.query(User).filter(User.username == LOGIN).first()
if not user:
    print("Пользователь не найден!"); raise SystemExit(1)

user.password_hash = get_password_hash(NEW_PASSWORD)
user.is_active = True
user.failed_login_count = 0
user.locked_until = None
db.commit()
print(f"1) Пароль для {LOGIN!r} сброшен")

auth = AuthService(db)
try:
    u = auth.authenticate_user(LOGIN, NEW_PASSWORD)
    print(f"2) Вход ПОДТВЕРЖДЁН программно: user_id={u.id}")
    print("   → Теперь входите в desktop с этим паролем")
except Exception as e:
    print(f"2) FAIL: {e}")