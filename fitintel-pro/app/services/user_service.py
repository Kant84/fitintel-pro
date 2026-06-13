# app/services/user_service.py

# импорт datetime и timezone для отметки времени назначения роли
from datetime import datetime, timezone

# импорт HTTPException и status для API-ошибок
from fastapi import HTTPException, status

# импорт Session для типизации SQLAlchemy-сессии
from sqlalchemy.orm import Session

# импорт функции хеширования пароля
from app.core.security import get_password_hash

# импорт модели пользователя
from app.models.user import User

# импорт модели связи пользователя и роли
from app.models.user_role import UserRole

# импорт репозиториев
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


# сервис пользователей
class UserService:
    # конструктор принимает SQLAlchemy-сессию
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

        # создаём репозиторий пользователей
        self.user_repository = UserRepository(db)

        # создаём репозиторий ролей
        self.role_repository = RoleRepository(db)

    # ============================================================
    # БАЗОВОЕ ЧТЕНИЕ
    # ============================================================

    # метод возвращает одного пользователя по id
    def get_user_by_id(self, user_id: str) -> User:
        # получаем пользователя вместе с ролями и правами
        user = self.user_repository.get_by_id_with_roles_permissions(user_id)

        # если пользователь не найден — возвращаем 404
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        # возвращаем найденного пользователя
        return user

    # метод возвращает список пользователей
    def list_users(self, offset: int = 0, limit: int = 100):
        # возвращаем список из репозитория
        return self.user_repository.list_with_roles_permissions(
            offset=offset,
            limit=limit,
        )

    # ============================================================
    # СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
    # ============================================================

    # метод создаёт пользователя
    def create_user(
        self,
        email: str | None,
        username: str | None,
        password: str,
        is_active: bool = True,
    ) -> User:
        # проверяем, что хотя бы один идентификатор задан
        if not email and not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нужно указать хотя бы email или username",
            )

        # если email передан — проверяем уникальность
        if email and self.user_repository.email_exists(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует",
            )

        # если username передан — проверяем уникальность
        if username and self.user_repository.username_exists(username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким username уже существует",
            )

        # создаём объект пользователя
        user = User(
            # сохраняем email
            email=email,
            # сохраняем username
            username=username,
            # сохраняем хеш пароля
            password_hash=get_password_hash(password),
            # сохраняем флаг активности
            is_active=is_active,
        )

        # сохраняем пользователя в БД
        return self.user_repository.add(user)

    # ============================================================
    # АДМИНИСТРАТИВНОЕ ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
    # ============================================================

    # метод обновляет пользователя администратором
    def update_user(
        self,
        user_id: str,
        email: str | None = None,
        username: str | None = None,
        is_active: bool | None = None,
    ) -> User:
        # получаем пользователя из БД
        user = self.get_user_by_id(user_id)

        # если email передан и отличается — проверяем уникальность и обновляем
        if email is not None and email != user.email:
            if self.user_repository.email_exists(email, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким email уже существует",
                )
            user.email = email

        # если username передан и отличается — проверяем уникальность и обновляем
        if username is not None and username != user.username:
            if self.user_repository.username_exists(username, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким username уже существует",
                )
            user.username = username

        # если флаг активности передан — обновляем его
        if is_active is not None:
            user.is_active = is_active

        # сохраняем изменения
        return self.user_repository.save(user)

    # ============================================================
    # SELF-SERVICE ОБНОВЛЕНИЕ СВОЕГО ПРОФИЛЯ
    # ============================================================

    # метод обновляет профиль текущего пользователя
    def update_own_profile(
        self,
        user: User,
        username: str | None = None,
        email: str | None = None,
    ) -> User:
        # если email передан и отличается — проверяем уникальность
        if email is not None and email != user.email:
            if self.user_repository.email_exists(email, exclude_user_id=str(user.id)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким email уже существует",
                )
            user.email = email

        # если username передан и отличается — проверяем уникальность
        if username is not None and username != user.username:
            if self.user_repository.username_exists(username, exclude_user_id=str(user.id)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким username уже существует",
                )
            user.username = username

        # сохраняем изменения
        return self.user_repository.save(user)

    # ============================================================
    # ДЕАКТИВАЦИЯ ПОЛЬЗОВАТЕЛЯ
    # ============================================================

    # метод деактивирует пользователя
    def deactivate_user(self, user_id: str) -> User:
        # получаем пользователя
        user = self.get_user_by_id(user_id)

        # если пользователь уже деактивирован — просто возвращаем его
        if not bool(getattr(user, "is_active", True)):
            return user

        # отключаем пользователя
        user.is_active = False

        # сохраняем изменения
        return self.user_repository.save(user)

    # ============================================================
    # РОЛИ ПОЛЬЗОВАТЕЛЯ
    # ============================================================

    # метод назначает роль пользователю
    def assign_role(
        self,
        user_id: str,
        role_code: str,
        assigned_by_user_id: str | None = None,
    ) -> User:
        # получаем пользователя
        user = self.get_user_by_id(user_id)

        # ищем роль по коду
        role = self.role_repository.get_by_code(role_code)

        # если роль не найдена — возвращаем 404
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Роль не найдена",
            )

        # проверяем, не назначена ли уже эта роль
        existing_link = self.user_repository.get_user_role_link(
            user_id=str(user.id),
            role_id=str(role.id),
        )

        # если связь уже есть — возвращаем 409
        if existing_link is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Эта роль уже назначена пользователю",
            )

        # создаём новую связь пользователя и роли
        user_role = UserRole(
            # пользователь
            user_id=user.id,
            # роль
            role_id=role.id,
            # кто назначил роль
            assigned_by_user_id=assigned_by_user_id,
            # когда назначили роль
            assigned_at=datetime.now(timezone.utc),
        )

        # сохраняем связь в БД
        self.user_repository.add_user_role(user_role)

        # возвращаем пользователя уже с новой ролью
        return self.get_user_by_id(str(user.id))

    # метод снимает роль с пользователя
    def revoke_role(self, user_id: str, role_code: str) -> User:
        # получаем пользователя
        user = self.get_user_by_id(user_id)

        # ищем роль по коду
        role = self.role_repository.get_by_code(role_code)

        # если роль не найдена — возвращаем 404
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Роль не найдена",
            )

        # ищем связь пользователя и роли
        existing_link = self.user_repository.get_user_role_link(
            user_id=str(user.id),
            role_id=str(role.id),
        )

        # если связи нет — возвращаем 404
        if existing_link is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="У пользователя нет такой роли",
            )

        # удаляем связь
        self.user_repository.delete_user_role(existing_link)

        # возвращаем пользователя уже без этой роли
        return self.get_user_by_id(str(user.id))

    # ============================================================
    # СБОРКА ОТВЕТОВ API
    # ============================================================

    # метод строит словарь ответа пользователя
    def build_user_response(self, user) -> dict:
        # множество кодов ролей для защиты от дублей
        seen_role_codes: set[str] = set()

        # множество кодов прав для защиты от дублей
        seen_permission_codes: set[str] = set()

        # итоговый список ролей
        roles: list[dict] = []

        # итоговый список прав
        permissions: list[dict] = []

        # получаем связи пользователя с ролями
        user_roles = getattr(user, "user_roles", []) or []

        # обходим связи пользователя с ролями
        for user_role in user_roles:
            # получаем объект роли
            role = getattr(user_role, "role", None)

            # если роли нет — пропускаем
            if role is None:
                continue

            # получаем код роли
            role_code = getattr(role, "code", None)

            # если код роли есть и ещё не добавлен — добавляем
            if role_code and str(role_code) not in seen_role_codes:
                seen_role_codes.add(str(role_code))
                roles.append(
                    {
                        "code": str(role_code),
                        "name": getattr(role, "name", None),
                    }
                )

            # получаем связи роли с правами
            role_permissions = getattr(role, "role_permissions", []) or []

            # обходим связи роли с правами
            for role_permission in role_permissions:
                # получаем объект permission
                permission = getattr(role_permission, "permission", None)

                # если permission отсутствует — пропускаем
                if permission is None:
                    continue

                # получаем код права
                permission_code = getattr(permission, "code", None)

                # если кода нет — пропускаем
                if not permission_code:
                    continue

                # если уже добавляли — пропускаем
                if str(permission_code) in seen_permission_codes:
                    continue

                # помечаем как добавленное
                seen_permission_codes.add(str(permission_code))

                # добавляем право в итоговый список
                permissions.append(
                    {
                        "code": str(permission_code),
                        "name": getattr(permission, "name", None),
                    }
                )

        # возвращаем итоговый словарь
        return {
            "id": user.id,
            "email": getattr(user, "email", None),
            "username": getattr(user, "username", None),
            "is_active": bool(getattr(user, "is_active", True)),
            "roles": roles,
            "permissions": permissions,
        }

    # метод строит ответ для списка пользователей
    def build_user_list_response(self, users: list) -> dict:
        # собираем элементы списка
        items = [self.build_user_response(user) for user in users]

        # возвращаем итоговую структуру
        return {
            "items": items,
            "count": len(items),
        }