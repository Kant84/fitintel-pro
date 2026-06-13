# app/services/rbac_service.py

# Импорт UUID для идентификаторов.
from uuid import UUID

# Импорт select и func для SQLAlchemy-запросов.
from sqlalchemy import select, func

# Импорт Session и selectinload для загрузки связанных объектов.
from sqlalchemy.orm import Session, selectinload

# Импорт HTTPException и status для понятных API-ошибок.
from fastapi import HTTPException, status

# Импорт ORM-моделей.
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.permission import Permission


class RBACService:
    """
    Сервис чтения и объяснения RBAC-структуры.

    Что умеет:
    - загружать пользователя вместе с ролями и правами
    - получать роли пользователя
    - получать итоговые права пользователя
    - строить матрицу ролей и прав
    - проверять доступ пользователя к одному праву
    - подробно объяснять доступ
    - показывать полный RBAC-снимок пользователя
    - показывать недостающие права
    - проверять целостность RBAC
    """

    def __init__(self, db: Session):
        # Сохраняем текущую сессию БД.
        self.db = db

    # ============================================================
    # БАЗОВАЯ ЗАГРУЗКА RBAC-СТРУКТУРЫ
    # ============================================================

    def get_user_with_rbac(self, user_id: UUID) -> User:
        """
        Загружает пользователя вместе с ролями и permission.
        """

        # Формируем запрос:
        # - пользователь
        # - связи user_roles
        # - роли
        # - связи role_permissions
        # - permissions
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRole.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )

        # Выполняем запрос.
        user = self.db.execute(stmt).scalar_one_or_none()

        # Если пользователь не найден — возвращаем 404.
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Возвращаем найденного пользователя.
        return user

    # ============================================================
    # РОЛИ И ПРАВА ПОЛЬЗОВАТЕЛЯ
    # ============================================================

    def get_user_roles(self, user_id: UUID) -> list[Role]:
        """
        Возвращает список ролей пользователя.
        """

        # Загружаем пользователя вместе с RBAC-структурой.
        user = self.get_user_with_rbac(user_id)

        # Возвращаем список ролей.
        return list(user.roles)

    def get_user_permissions(self, user_id: UUID) -> list[Permission]:
        """
        Возвращает итоговый список уникальных permission пользователя.
        """

        # Загружаем пользователя вместе с RBAC-структурой.
        user = self.get_user_with_rbac(user_id)

        # Словарь нужен для удаления дублей по коду permission.
        unique_permissions: dict[str, Permission] = {}

        # Проходим по ролям пользователя.
        for role in user.roles:
            # Проходим по правам этой роли.
            for permission in role.permissions:
                # Сохраняем permission по его коду.
                unique_permissions[permission.code] = permission

        # Сортируем итоговые права по коду.
        permissions = sorted(
            unique_permissions.values(),
            key=lambda item: item.code,
        )

        # Возвращаем список permission.
        return permissions

    # ============================================================
    # МАТРИЦА РОЛЕЙ И ПРАВ
    # ============================================================

    def get_roles_matrix(self) -> list[Role]:
        """
        Возвращает все роли вместе с их permission.
        """

        # Формируем запрос ролей вместе со связями role_permissions -> permission.
        stmt = (
            select(Role)
            .options(
                selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
            .order_by(Role.code)
        )

        # Выполняем запрос.
        roles = self.db.execute(stmt).scalars().unique().all()

        # Возвращаем список ролей.
        return roles

    # ============================================================
    # ПРОВЕРКА И ОБЪЯСНЕНИЕ ДОСТУПА
    # ============================================================

    def check_user_access(self, user_id: UUID, permission_code: str) -> dict:
        """
        Базовая проверка доступа пользователя к одному permission.
        """

        # Загружаем пользователя с полной RBAC-структурой.
        user = self.get_user_with_rbac(user_id)

        # Список ролей, через которые выдаётся нужное право.
        granted_via_roles: list[str] = []

        # Собираем все роли пользователя.
        all_roles = [role.code for role in user.roles]

        # Словарь итоговых permission без дублей.
        unique_permissions: dict[str, Permission] = {}

        # Проходим по ролям пользователя.
        for role in user.roles:
            # Флаг, показывает даёт ли эта роль искомое право.
            role_has_permission = False

            # Проходим по permission роли.
            for permission in role.permissions:
                # Добавляем право в общий словарь.
                unique_permissions[permission.code] = permission

                # Если нашли искомое permission — отмечаем.
                if permission.code == permission_code:
                    role_has_permission = True

            # Если роль даёт нужное право — добавляем код роли.
            if role_has_permission:
                granted_via_roles.append(role.code)

        # Собираем список всех кодов permission пользователя.
        all_permissions = sorted(unique_permissions.keys())

        # Возвращаем базовый результат.
        return {
            "user_id": user.id,
            "permission_code": permission_code,
            "has_access": permission_code in all_permissions,
            "granted_via_roles": granted_via_roles,
            "all_roles": all_roles,
            "all_permissions": all_permissions,
        }

    def explain_user_access(self, user_id: UUID, permission_code: str) -> dict:
        """
        Подробно объясняет, почему доступ есть или почему его нет.
        """

        # Получаем базовый результат проверки доступа.
        result = self.check_user_access(
            user_id=user_id,
            permission_code=permission_code,
        )

        # Получаем роли пользователя.
        all_roles = result["all_roles"]

        # Получаем все permission пользователя.
        all_permissions = result["all_permissions"]

        # Формируем объяснение.
        if result["has_access"]:
            reason = "Permission granted"
        else:
            if not all_roles:
                reason = "User has no roles assigned"
            else:
                reason = "Permission not granted to user via assigned roles"

        # Возвращаем расширенный explain-ответ.
        return {
            "user_id": result["user_id"],
            "permission_code": result["permission_code"],
            "has_access": result["has_access"],
            "reason": reason,
            "granted_via_roles": result["granted_via_roles"],
            "all_roles": all_roles,
            "all_permissions": all_permissions,
            "checked_roles_count": len(all_roles),
            "checked_permissions_count": len(all_permissions),
        }

    def get_user_rbac_snapshot(self, user_id: UUID) -> dict:
        """
        Возвращает полный RBAC-снимок пользователя:
        - роли
        - итоговые permission
        """

        # Загружаем пользователя с ролями и правами.
        user = self.get_user_with_rbac(user_id)

        # Формируем список ролей пользователя.
        roles_payload = []
        for role in user.roles:
            roles_payload.append(
                {
                    "id": role.id,
                    "code": role.code,
                    "name": getattr(role, "name", None),
                    "is_system": role.is_system,
                }
            )

        # Собираем уникальные права.
        unique_permissions: dict[str, Permission] = {}

        for role in user.roles:
            for permission in role.permissions:
                unique_permissions[permission.code] = permission

        # Формируем список permission.
        permissions_payload = []
        for permission in sorted(unique_permissions.values(), key=lambda item: item.code):
            permissions_payload.append(
                {
                    "id": permission.id,
                    "code": permission.code,
                    "name": getattr(permission, "name", None),
                    "description": getattr(permission, "description", None),
                }
            )

        # Возвращаем полный снимок.
        return {
            "user_id": user.id,
            "roles": roles_payload,
            "permissions": permissions_payload,
        }

    def get_missing_permissions(self, user_id: UUID, required_permissions: list[str]) -> dict:
        """
        Возвращает список permission, которых не хватает пользователю.
        """

        # Получаем итоговые permission пользователя.
        existing_permissions = [item.code for item in self.get_user_permissions(user_id)]

        # Получаем роли пользователя.
        all_roles = [role.code for role in self.get_user_roles(user_id)]

        # Вычисляем недостающие permission.
        missing_permissions = sorted(
            [code for code in required_permissions if code not in existing_permissions]
        )

        # Возвращаем результат.
        return {
            "user_id": user_id,
            "missing_permissions": missing_permissions,
            "existing_permissions": sorted(existing_permissions),
            "all_roles": all_roles,
        }

    def debug_access(self, user_id: UUID, required_permissions: list[str]) -> dict:
        """
        Удобный debug-метод:
        показывает роли, права и каких прав не хватает.
        """

        # Получаем роли пользователя.
        roles = [role.code for role in self.get_user_roles(user_id)]

        # Получаем итоговые permission пользователя.
        permissions = [item.code for item in self.get_user_permissions(user_id)]

        # Вычисляем недостающие права.
        missing_permissions = sorted(
            [code for code in required_permissions if code not in permissions]
        )

        # Возвращаем debug-информацию.
        return {
            "user_id": user_id,
            "roles": sorted(roles),
            "permissions": sorted(permissions),
            "missing_permissions": missing_permissions,
        }

    # ============================================================
    # HEALTH RBAC
    # ============================================================

    def check_rbac_health(self) -> dict:
        """
        Проверка базовой целостности RBAC.
        """

        # Собираем найденные проблемы.
        issues = []

        # Проверяем наличие роли admin.
        admin = self.db.execute(
            select(Role).where(Role.code == "admin")
        ).scalar_one_or_none()

        if admin is None:
            issues.append("Admin role missing")
        else:
            # Считаем пользователей с ролью admin.
            count = self.db.execute(
                select(func.count())
                .select_from(UserRole)
                .where(UserRole.role_id == admin.id)
            ).scalar_one()

            if count < 1:
                issues.append("No admin users")

        # Проверяем наличие permission system.admin.
        perm = self.db.execute(
            select(Permission).where(Permission.code == "system.admin")
        ).scalar_one_or_none()

        if perm is None:
            issues.append("Permission 'system.admin' missing")
        else:
            # Считаем роли, у которых есть это permission.
            count = self.db.execute(
                select(func.count())
                .select_from(RolePermission)
                .where(RolePermission.permission_id == perm.id)
            ).scalar_one()

            if count < 1:
                issues.append("No role has 'system.admin' permission")

        # Возвращаем итоговый статус.
        return {
            "status": "ok" if not issues else "broken",
            "issues": issues,
        }
        
    def check_user_access_with_audit(
        self,
        user_id: UUID,
        permission_code: str,
        audit_service
    ) -> dict:

        result = self.explain_user_access(user_id, permission_code)

        if result["has_access"]:
            audit_service.log(
                action="access.check.allowed",
                status="success",
                actor_user_id=user_id,
                message=result["reason"],
                after_data=result,
            )
        
        else:
            audit_service.log(
                action="access.check.denied",
                status="denied",
                actor_user_id=user_id,
                message=result["reason"],
                after_data=result,
            )

        return result