# app/repositories/role_repository.py

# импорт select для SQLAlchemy-запросов
from sqlalchemy import select

# импорт Session для типизации SQLAlchemy-сессии
from sqlalchemy.orm import Session

# импорт модели роли
from app.models.role import Role


# репозиторий ролей
class RoleRepository:
    # конструктор принимает активную SQLAlchemy-сессию
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

    # метод ищет роль по id
    def get_by_id(self, role_id: str) -> Role | None:
        # создаём SQL-запрос
        statement = select(Role).where(Role.id == role_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем роль или None
        return result.scalar_one_or_none()

    # метод ищет роль по коду
    def get_by_code(self, code: str) -> Role | None:
        # создаём SQL-запрос
        statement = select(Role).where(Role.code == code)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем роль или None
        return result.scalar_one_or_none()