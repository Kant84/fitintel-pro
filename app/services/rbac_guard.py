# app/services/rbac_guard.py

from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole


CRITICAL_ROLE_CODES = {"admin", "owner", "device"}

CRITICAL_PERMISSION_CODES = {
    "system.admin",
    "roles.manage",
    "users.read",
    "users.create",
    "users.update",
}


class RBACGuardService:
    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    def _is_critical_role(self, role: Role) -> bool:
        return role.code in CRITICAL_ROLE_CODES

    def _is_critical_permission(self, permission: Permission) -> bool:
        return permission.code in CRITICAL_PERMISSION_CODES

    def _count_users_with_role(self, role_id: UUID) -> int:
        stmt = select(func.count()).select_from(UserRole).where(
            UserRole.role_id == role_id
        )
        return int(self.db.execute(stmt).scalar_one() or 0)

    def _count_roles_with_permission(self, permission_id: UUID) -> int:
        stmt = select(func.count()).select_from(RolePermission).where(
            RolePermission.permission_id == permission_id
        )
        return int(self.db.execute(stmt).scalar_one() or 0)

    def _get_role_by_code(self, code: str) -> Optional[Role]:
        stmt = select(Role).where(Role.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def _get_permission_by_code(self, code: str) -> Optional[Permission]:
        stmt = select(Permission).where(Permission.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    # ============================================================
    # ОСНОВНЫЕ ЗАЩИТЫ
    # ============================================================

    def check_can_delete_role(self, role: Role) -> None:
        """
        Полная защита удаления роли
        """

        # Жёсткая защита admin
        if role.code == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя удалить роль 'admin'.",
            )

        # Системные роли нельзя удалять
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Системную роль '{role.code}' удалять нельзя.",
            )

        # Критичные роли нельзя удалять
        if self._is_critical_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Критичную роль '{role.code}' удалять нельзя.",
            )

    def check_can_modify_role(
        self,
        role: Role,
        new_code: Optional[str] = None,
        new_is_system: Optional[bool] = None,
    ) -> None:
        """
        Проверка безопасного изменения роли.
        """

        if self._is_critical_role(role):
            if new_code is not None and new_code != role.code:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"У роли '{role.code}' нельзя менять code.",
                )

            if new_is_system is not None and new_is_system != role.is_system:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"У роли '{role.code}' нельзя менять is_system.",
                )

    def check_can_assign_role(self, actor_user_id: UUID, role: Role) -> None:
        """
        Проверка безопасного назначения роли.
        На текущем этапе запрещаем назначение критичных ролей
        """

        if role.code == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Назначение роли 'admin' через данный endpoint запрещено.",
            )

        if role.code == "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Назначение роли 'owner' через данный endpoint запрещено.",
            )

        if role.code == "device":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Назначение роли 'device' через данный endpoint запрещено.",
            )

    def check_can_revoke_role(self, user_id: UUID, role: Role) -> None:
        """
        Защита последнего admin
        """

        if role.code != "admin":
            return

        admin_count = self._count_users_with_role(role.id)

        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя снять последнего admin пользователя.",
            )

    def check_can_remove_permission_from_role(
        self,
        role: Role,
        permission: Permission,
    ) -> None:
        """
        Проверка безопасного удаления permission у роли.
        """

        if role.code == "admin" and self._is_critical_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Нельзя удалить критичное право '{permission.code}' у admin.",
            )

        if permission.code == "system.admin":
            count = self._count_roles_with_permission(permission.id)

            if count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нельзя удалить последнее назначение system.admin.",
                )

    # ============================================================
    # RBAC HEALTH
    # ============================================================

    def check_rbac_matrix_health(self) -> None:
        """
        Проверка целостности RBAC.
        Пока оставляем 400, потому что это уже состояние системы,
        а не обычный запрет действия пользователю.
        """

        admin_role = self._get_role_by_code("admin")

        if admin_role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RBAC сломан: нет роли admin",
            )

        admin_users = self._count_users_with_role(admin_role.id)

        if admin_users < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RBAC сломан: нет admin пользователей",
            )

        system_admin = self._get_permission_by_code("system.admin")

        if system_admin is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RBAC сломан: нет permission system.admin",
            )

        roles_with_permission = self._count_roles_with_permission(system_admin.id)

        if roles_with_permission < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RBAC сломан: system.admin никому не назначен",
            )
    def check_can_reset_password(self, actor_user, target_user) -> None:
        """
        Проверка безопасного административного сброса пароля.
        """

        # Нельзя использовать admin reset endpoint для самого себя.
        if actor_user.id == target_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для смены своего пароля используйте self-service endpoint.",
            )

        # Собираем реальные role codes пользователя.
        actor_role_codes: set[str] = set()

        for user_role in getattr(actor_user, "user_roles", []) or []:
            role = getattr(user_role, "role", None)

            if role is None:
                continue

            role_code = getattr(role, "code", None)

            if role_code:
                actor_role_codes.add(str(role_code))

        # Проверяем наличие admin-роли.
        if "admin" not in actor_role_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на сброс пароля.",
            )