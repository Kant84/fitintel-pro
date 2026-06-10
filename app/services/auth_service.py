# app/services/auth_service.py

# импорт timedelta для расчёта срока жизни токена
from datetime import timedelta

# импорт HTTPException и status для API-ошибок
from fastapi import HTTPException, status

# импорт Session для типизации работы с БД
from sqlalchemy.orm import Session

# импорт функций безопасности
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    verify_password,
    get_password_hash,
)

# импорт репозитория пользователей
from app.repositories.user_repository import UserRepository

from app.services.rbac_guard import RBACGuardService

# сервис аутентификации
class AuthService:
    # конструктор принимает SQLAlchemy-сессию
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

        # создаём репозиторий пользователей
        self.user_repository = UserRepository(db)

    # ============================================================
    # БАЗОВЫЕ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    # метод получает хеш пароля из объекта пользователя
    def get_user_password_hash(self, user) -> str | None:
        # если у пользователя есть поле password_hash, возвращаем его
        if hasattr(user, "password_hash"):
            return getattr(user, "password_hash")

        # если поле отсутствует, возвращаем None
        return None

    # метод возвращает признак активности пользователя
    def is_user_active(self, user) -> bool:
        # если поле is_active есть, возвращаем его значение
        if hasattr(user, "is_active"):
            return bool(getattr(user, "is_active"))

        # если поля нет, считаем пользователя активным
        return True

    # метод возвращает список ролей пользователя
    def get_user_roles(self, user) -> list[str]:
        # создаём пустое множество для уникальных кодов ролей
        role_codes: set[str] = set()

        # если у пользователя есть отношение user_roles
        if hasattr(user, "user_roles"):
            # получаем список связей пользователя с ролями
            user_roles = getattr(user, "user_roles") or []

            # обходим все связи пользователя с ролями
            for user_role in user_roles:
                # получаем объект роли из связи
                role = getattr(user_role, "role", None)

                # если роль отсутствует, пропускаем
                if role is None:
                    continue

                # если у роли есть код и он не пустой, добавляем его
                if hasattr(role, "code") and getattr(role, "code"):
                    role_codes.add(str(getattr(role, "code")))

        # возвращаем отсортированный список кодов ролей
        return sorted(role_codes)

    # метод возвращает список прав пользователя
    def get_user_permissions(self, user) -> list[str]:
        # создаём пустое множество для уникальных кодов прав
        permission_codes: set[str] = set()

        # если у пользователя есть отношение user_roles
        if hasattr(user, "user_roles"):
            # получаем список связей пользователя с ролями
            user_roles = getattr(user, "user_roles") or []

            # обходим все связи пользователя с ролями
            for user_role in user_roles:
                # получаем объект роли из связи
                role = getattr(user_role, "role", None)

                # если роль отсутствует, пропускаем
                if role is None:
                    continue

                # если у роли есть отношение role_permissions
                if hasattr(role, "role_permissions"):
                    # получаем список связей роли с правами
                    role_permissions = getattr(role, "role_permissions") or []

                    # обходим все связи роли с правами
                    for role_permission in role_permissions:
                        # получаем объект permission из связи
                        permission = getattr(role_permission, "permission", None)

                        # если permission отсутствует, пропускаем
                        if permission is None:
                            continue

                        # если у permission есть код и он не пустой, добавляем его
                        if hasattr(permission, "code") and getattr(permission, "code"):
                            permission_codes.add(str(getattr(permission, "code")))

        # возвращаем отсортированный список кодов прав
        return sorted(permission_codes)

    # метод проверяет, есть ли у пользователя конкретная роль
    def has_role(self, user, required_role: str) -> bool:
        # получаем все роли пользователя
        user_roles = self.get_user_roles(user)

        # проверяем наличие нужной роли
        return required_role in user_roles

    # метод проверяет, есть ли у пользователя конкретное право
    def has_permission(self, user, required_permission: str) -> bool:
        # получаем все права пользователя
        user_permissions = self.get_user_permissions(user)

        # проверяем наличие нужного права
        return required_permission in user_permissions

    # ============================================================
    # АУТЕНТИФИКАЦИЯ
    # ============================================================

    # метод аутентифицирует пользователя по логину и паролю
    def authenticate_user(self, login: str, password: str):
        # ищем пользователя по login
        user = self.user_repository.get_by_login(login)

        # если пользователь не найден, возвращаем None
        if user is None:
            return None

        # получаем хеш пароля пользователя
        password_hash = self.get_user_password_hash(user)

        # если хеш отсутствует, возвращаем None
        if not password_hash:
            return None

        # если пароль не прошёл проверку, возвращаем None
        if not verify_password(password, password_hash):
            return None

        # если пользователь неактивен, тоже не пускаем
        if not self.is_user_active(user):
            return None

        # если всё хорошо, возвращаем пользователя
        return user

    # метод создаёт access token для пользователя
    def create_user_access_token(self, user) -> str:
        # создаём токен с subject равным id пользователя
        token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        # возвращаем токен
        return token

    # метод собирает безопасные данные пользователя для ответа API
    def build_current_user_response(self, user) -> dict:
        # возвращаем словарь без чувствительных полей
        return {
            # UUID пользователя в строковом виде
            "id": str(getattr(user, "id")),
            # email пользователя
            "email": getattr(user, "email", None),
            # username пользователя
            "username": getattr(user, "username", None),
            # активен ли пользователь
            "is_active": self.is_user_active(user),
            # список ролей
            "roles": self.get_user_roles(user),
            # список итоговых прав
            "permissions": self.get_user_permissions(user),
        }

    # ============================================================
    # ОПЕРАЦИИ С ПАРОЛЯМИ
    # ============================================================

    # метод меняет пароль текущего пользователя
    def change_own_password(
        self,
        user,
        current_password: str,
        new_password: str,
    ) -> bool:
        # получаем текущий хеш пароля
        password_hash = self.get_user_password_hash(user)

        # если хеш отсутствует — это ошибка состояния
        if not password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У пользователя отсутствует пароль",
            )

        # если текущий пароль неверный — запрещаем смену
        if not verify_password(current_password, password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный текущий пароль",
            )

        # если новый пароль совпадает со старым — запрещаем такую смену
        if verify_password(new_password, password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Новый пароль не должен совпадать с текущим",
            )

        # сохраняем новый хеш пароля
        user.password_hash = get_password_hash(new_password)

        # если в модели есть флаг обязательной смены пароля — снимаем его
        if hasattr(user, "force_password_change"):
            user.force_password_change = False

        # сохраняем изменения
        self.db.commit()

        # обновляем объект после commit
        self.db.refresh(user)

        # возвращаем успешный результат
        return True

    # метод выполняет административный сброс пароля
    def admin_reset_password(
        self,
        actor_user,
        target_user,
        new_password: str,
        force_password_change: bool = True,
    ) -> bool:
        # создаём guard-сервис
        guard = RBACGuardService(self.db)

        # проверяем, можно ли выполнять reset password
        guard.check_can_reset_password(
            actor_user=actor_user,
            target_user=target_user,
        )

        # защита от пустого пароля
        if not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Новый пароль не может быть пустым",
            )

        # сохраняем новый хеш пароля
        target_user.password_hash = get_password_hash(new_password)

        # если в модели есть флаг обязательной смены пароля
        if hasattr(target_user, "force_password_change"):
            target_user.force_password_change = force_password_change

        self.db.commit()
        self.db.refresh(target_user)

        return True