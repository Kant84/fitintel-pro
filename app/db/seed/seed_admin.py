# app\db\seed\seed_admin.py
import os

# импорт модели пользователя
from app.models.user import User

# импорт модели роли
from app.models.role import Role

# импорт модели связи пользователь-роль
from app.models.user_role import UserRole

# импорт функции хеширования пароля
from app.core.security import get_password_hash


# стартовые данные администратора (переопределяются переменными окружения SEED_ADMIN_*)
DEFAULT_ADMIN_EMAIL    = os.environ.get("SEED_ADMIN_EMAIL",    "admin@fitnexus.ru")
DEFAULT_ADMIN_USERNAME = os.environ.get("SEED_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "Admin123!ChangeMe")


# функция создаёт первичного администратора
def seed_admin(db) -> None:
    # ищем пользователя по email
    existing_user = db.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL).first()

    # если пользователь уже есть, повторно не создаём
    if existing_user:
        return

    # создаём нового администратора
    admin_user = User(
        email=DEFAULT_ADMIN_EMAIL,
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=get_password_hash(DEFAULT_ADMIN_PASSWORD),
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )

    # добавляем пользователя в сессию
    db.add(admin_user)

    # фиксируем, чтобы у пользователя появился id
    db.commit()

    # обновляем объект из базы после commit
    db.refresh(admin_user)

    # ищем роль admin
    admin_role = db.query(Role).filter(Role.code == "admin").first()

    # если роли admin нет, завершаем функцию
    if not admin_role:
        return

    # проверяем, есть ли уже связь пользователя и роли
    existing_link = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == admin_user.id,
            UserRole.role_id == admin_role.id,
        )
        .first()
    )

    # если связь уже существует, повторно не создаём
    if existing_link:
        return

    # создаём связь пользователя с ролью admin
    user_role = UserRole(
        user_id=admin_user.id,
        role_id=admin_role.id,
        assigned_by_user_id=None,
    )

    # добавляем связь в сессию
    db.add(user_role)

    # фиксируем изменения
    db.commit()


if __name__ == "__main__":
    # автономный запуск: python -m app.db.seed.seed_admin
    # креды задаются переменными окружения SEED_ADMIN_EMAIL / SEED_ADMIN_USERNAME / SEED_ADMIN_PASSWORD
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        seed_admin(db)
        print(f"OK: admin готов -> логин: {DEFAULT_ADMIN_USERNAME} (пароль задан, смените после входа!)")
    finally:
        db.close()