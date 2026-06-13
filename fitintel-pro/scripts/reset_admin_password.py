# scripts/reset_admin_password.py

# импорт системного модуля для корректного импорта app
import sys

# импорт pathlib для работы с путями
from pathlib import Path

# добавляем корень проекта в sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# импорт select из SQLAlchemy
from sqlalchemy import select

# импорт сессии БД
from app.db.session import SessionLocal

# импорт модели пользователя
from app.models.user import User

# импорт функции хеширования пароля
from app.core.security import get_password_hash


def main() -> None:
    """
    Скрипт сбрасывает пароль администратора.
    """

    # логин администратора
    admin_username = "admin"

    # новый пароль администратора
    new_password = "admin123"

    # создаём сессию БД
    db = SessionLocal()

    try:
        # ищем пользователя по username
        statement = select(User).where(User.username == admin_username)
        result = db.execute(statement)
        user = result.scalar_one_or_none()

        # если пользователь не найден, сообщаем об этом
        if user is None:
            print("Ошибка: пользователь admin не найден")
            return

        # обновляем хеш пароля
        user.password_hash = get_password_hash(new_password)

        # на всякий случай убеждаемся, что пользователь активен
        if hasattr(user, "is_active"):
            user.is_active = True

        # сохраняем изменения
        db.commit()

        print("Пароль администратора успешно обновлён")
        print("Логин: admin")
        print("Пароль: admin123")

    except Exception as exc:
        db.rollback()
        print("Ошибка при обновлении пароля:", repr(exc))

    finally:
        db.close()


if __name__ == "__main__":
    main()