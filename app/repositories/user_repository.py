# app/repositories/user_repository.py

# импорт or_ и select из SQLAlchemy
from sqlalchemy import or_, select

# импорт Session и selectinload для работы с БД и подгрузки связей
from sqlalchemy.orm import Session, selectinload

# импорт модели пользователя
from app.models.user import User

# импорт моделей связей
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.role_permission import RolePermission


# репозиторий пользователя
class UserRepository:
    # конструктор принимает активную SQLAlchemy-сессию
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

    # метод ищет пользователя по id
    def get_by_id(self, user_id: str) -> User | None:
        # создаём SQL-запрос
        statement = select(User).where(User.id == user_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем пользователя или None
        return result.scalar_one_or_none()

    # метод ищет пользователя по id и сразу подгружает роли и права
    def get_by_id_with_roles_permissions(self, user_id: str) -> User | None:
        # создаём SQL-запрос
        statement = (
            select(User)
            .options(
                # загружаем связи user_roles
                selectinload(User.user_roles)
                # внутри связи загружаем роль
                .selectinload(UserRole.role)
                # внутри роли загружаем связи role_permissions
                .selectinload(Role.role_permissions)
                # внутри связи загружаем permission
                .selectinload(RolePermission.permission)
            )
            .where(User.id == user_id)
        )

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем пользователя или None
        return result.scalar_one_or_none()

    # метод возвращает список пользователей с ролями и правами
    def list_with_roles_permissions(
        self,
        offset: int = 0,
        limit: int = 100,
        role: str = None,
    ) -> list[User]:
        # создаём SQL-запрос
        statement = select(User).options(
            selectinload(User.user_roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
        
        # фильтрация по роли
        if role:
            statement = statement.join(User.user_roles).join(UserRole.role).where(Role.code == role)
        
        # сортируем по username для стабильного результата
        statement = statement.order_by(User.username)
        # применяем offset и limit
        statement = statement.offset(offset).limit(limit)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем список пользователей
        return list(result.scalars().all())

    # метод ищет пользователя по email
    def get_by_email(self, email: str) -> User | None:
        # если у модели нет поля email, возвращаем None
        if not hasattr(User, "email"):
            return None

        # создаём SQL-запрос
        statement = select(User).where(User.email == email)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем пользователя или None
        return result.scalar_one_or_none()

    # метод ищет пользователя по username
    def get_by_username(self, username: str) -> User | None:
        # если у модели нет поля username, возвращаем None
        if not hasattr(User, "username"):
            return None

        # создаём SQL-запрос
        statement = select(User).where(User.username == username)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем пользователя или None
        return result.scalar_one_or_none()

    # метод ищет пользователя по login
    def get_by_login(self, login: str) -> User | None:
        # собираем условия поиска
        conditions = []

        # если есть email — добавляем поиск по email
        if hasattr(User, "email"):
            conditions.append(User.email == login)

        # если есть username — добавляем поиск по username
        if hasattr(User, "username"):
            conditions.append(User.username == login)

        # если условий нет, возвращаем None
        if not conditions:
            return None

        # создаём SQL-запрос
        statement = select(User).where(or_(*conditions))

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем пользователя или None
        return result.scalar_one_or_none()

    # метод проверяет, занят ли email
    def email_exists(self, email: str, exclude_user_id: str | None = None) -> bool:
        # создаём базовый запрос
        statement = select(User).where(User.email == email)

        # если нужно исключить пользователя — добавляем условие
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # если пользователь найден — email занят
        return result.scalar_one_or_none() is not None

    # метод проверяет, занят ли username
    def username_exists(self, username: str, exclude_user_id: str | None = None) -> bool:
        # создаём базовый запрос
        statement = select(User).where(User.username == username)

        # если нужно исключить пользователя — добавляем условие
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # если пользователь найден — username занят
        return result.scalar_one_or_none() is not None

    # метод ищет связь пользователя и роли
    def get_user_role_link(self, user_id: str, role_id: str) -> UserRole | None:
        # создаём SQL-запрос
        statement = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем связь или None
        return result.scalar_one_or_none()

    # метод добавляет пользователя в БД
    def add(self, user: User) -> User:
        # добавляем объект в сессию
        self.db.add(user)

        # сохраняем изменения
        self.db.commit()

        # перечитываем объект после commit
        self.db.refresh(user)

        # возвращаем объект
        return user

    # метод сохраняет изменения существующего пользователя
    def save(self, user: User) -> User:
        # сохраняем изменения
        self.db.commit()

        # перечитываем объект после commit
        self.db.refresh(user)

        # возвращаем объект
        return user

    # метод добавляет связь пользователя с ролью
    def add_user_role(self, user_role: UserRole) -> UserRole:
        # добавляем объект связи в сессию
        self.db.add(user_role)

        # сохраняем изменения
        self.db.commit()

        # обновляем объект после commit
        self.db.refresh(user_role)

        # возвращаем объект связи
        return user_role

    # метод удаляет связь пользователя с ролью
    def delete_user_role(self, user_role: UserRole) -> None:
        # удаляем объект связи
        self.db.delete(user_role)

        # сохраняем изменения
        self.db.commit()