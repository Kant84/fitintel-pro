# app/services/role_permission_service.py

# Импорт UUID для идентификаторов.
from uuid import UUID

# Импорт HTTPException и status для API-ошибок.
from fastapi import HTTPException, status

# Импорт select для SQLAlchemy-запросов.
from sqlalchemy import select

# Импорт Session для работы с БД.
from sqlalchemy.orm import Session

# Импорт моделей роли, permission и связи роль-право.
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission

# Импорт защитного сервиса RBAC.
from app.services.rbac_guard import RBACGuardService

# Импорт сервиса аудита.
from app.services.audit_service import AuditService


class RolePermissionService:
    """
    Сервис управления связями роль-право.
    """

    def __init__(self, db: Session):
        # Сохраняем текущую сессию БД.
        self.db = db

        # Создаём сервис защитных правил.
        self.guard = RBACGuardService(db)

        # Создаём сервис аудита.
        self.audit = AuditService(db)

    def add_permission_to_role(
        self,
        actor_user_id: UUID,
        role_id: UUID,
        permission_id: UUID,
    ) -> RolePermission:
        """
        Добавляет permission к роли.
        """

        try:
            # Ищем роль.
            role = self.db.get(Role, role_id)
            if role is None:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.add",
                    entity_type="role",
                    role_id=role_id,
                    permission_id=permission_id,
                    message="Role not found",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role not found",
                )

            # Ищем permission.
            permission = self.db.get(Permission, permission_id)
            if permission is None:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.add",
                    entity_type="permission",
                    role_id=role_id,
                    permission_id=permission_id,
                    message="Permission not found",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Permission not found",
                )

            # Проверяем guard.
            try:
                self.guard.check_can_add_permission_to_role(
                    role=role,
                    permission=permission,
                )
            except HTTPException as exc:
                self.db.rollback()

                self.audit.log_rbac_denied_action(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.add",
                    entity_type="role_permission",
                    role_id=role_id,
                    permission_id=permission_id,
                    message=str(exc.detail),
                    after_data={
                        "role_id": str(role_id),
                        "role_code": role.code,
                        "permission_id": str(permission_id),
                        "permission_code": permission.code,
                    },
                )
                raise

            # Проверяем, нет ли уже такой связи.
            stmt = select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
            existing_link = self.db.execute(stmt).scalar_one_or_none()

            if existing_link is not None:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.add",
                    entity_type="role_permission",
                    entity_id=existing_link.id,
                    role_id=role_id,
                    permission_id=permission_id,
                    message="Permission already assigned to role",
                    before_data={
                        "role_permission_id": str(existing_link.id),
                        "role_id": str(role_id),
                        "role_code": role.code,
                        "permission_id": str(permission_id),
                        "permission_code": permission.code,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Permission already assigned to role",
                )

            # Создаём новую связь.
            new_link = RolePermission(
                role_id=role_id,
                permission_id=permission_id,
            )

            self.db.add(new_link)
            self.db.commit()
            self.db.refresh(new_link)

            # Проверяем матрицу безопасности после изменения.
            try:
                self.guard.check_rbac_matrix_health()
            except HTTPException as exc:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.add.matrix_health_check",
                    entity_type="role_permission",
                    entity_id=new_link.id,
                    role_id=role_id,
                    permission_id=permission_id,
                    message=str(exc.detail),
                    after_data={
                        "role_permission_id": str(new_link.id),
                        "role_id": str(role_id),
                        "role_code": role.code,
                        "permission_id": str(permission_id),
                        "permission_code": permission.code,
                    },
                )
                raise

            # Логируем успех.
            self.audit.log_event(
                actor_user_id=actor_user_id,
                action="rbac.role_permission.added",
                entity_type="role_permission",
                entity_id=new_link.id,
                role_id=role_id,
                permission_id=permission_id,
                status="success",
                message="Permission added to role successfully",
                after_data={
                    "role_permission_id": str(new_link.id),
                    "role_id": str(role_id),
                    "role_code": role.code,
                    "permission_id": str(permission_id),
                    "permission_code": permission.code,
                },
            )

            return new_link

        except HTTPException:
            raise

        except Exception as exc:
            self.db.rollback()

            self.audit.log_rbac_error(
                actor_user_id=actor_user_id,
                action="rbac.role_permission.add",
                entity_type="role_permission",
                role_id=role_id,
                permission_id=permission_id,
                message=f"Unexpected error: {str(exc)}",
            )
            raise

    def remove_permission_from_role(
        self,
        actor_user_id: UUID,
        role_id: UUID,
        permission_id: UUID,
    ) -> None:
        """
        Удаляет permission у роли.
        """

        try:
            # Ищем роль.
            role = self.db.get(Role, role_id)
            if role is None:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.remove",
                    entity_type="role",
                    role_id=role_id,
                    permission_id=permission_id,
                    message="Role not found",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role not found",
                )

            # Ищем permission.
            permission = self.db.get(Permission, permission_id)
            if permission is None:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.remove",
                    entity_type="permission",
                    role_id=role_id,
                    permission_id=permission_id,
                    message="Permission not found",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Permission not found",
                )

            # Ищем связь роль-право.
            stmt = select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
            existing_link = self.db.execute(stmt).scalar_one_or_none()

            if existing_link is None:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.remove",
                    entity_type="role_permission",
                    role_id=role_id,
                    permission_id=permission_id,
                    message="Role permission link not found",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role permission link not found",
                )

            # Запоминаем состояние до удаления.
            before_data = {
                "role_permission_id": str(existing_link.id),
                "role_id": str(role_id),
                "role_code": role.code,
                "permission_id": str(permission_id),
                "permission_code": permission.code,
            }

            # Проверяем guard.
            try:
                self.guard.check_can_remove_permission_from_role(
                    role=role,
                    permission=permission,
                )
            except HTTPException as exc:
                self.db.rollback()

                self.audit.log_rbac_denied_action(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.remove",
                    entity_type="role_permission",
                    entity_id=existing_link.id,
                    role_id=role_id,
                    permission_id=permission_id,
                    message=str(exc.detail),
                    before_data=before_data,
                )
                raise

            # Удаляем связь.
            self.db.delete(existing_link)
            self.db.commit()

            # Проверяем матрицу безопасности после удаления.
            try:
                self.guard.check_rbac_matrix_health()
            except HTTPException as exc:
                self.audit.log_rbac_error(
                    actor_user_id=actor_user_id,
                    action="rbac.role_permission.remove.matrix_health_check",
                    entity_type="role_permission",
                    role_id=role_id,
                    permission_id=permission_id,
                    message=str(exc.detail),
                    before_data=before_data,
                )
                raise

            # Логируем успех.
            self.audit.log_event(
                actor_user_id=actor_user_id,
                action="rbac.role_permission.removed",
                entity_type="role_permission",
                role_id=role_id,
                permission_id=permission_id,
                status="success",
                message="Permission removed from role successfully",
                before_data=before_data,
            )

        except HTTPException:
            raise

        except Exception as exc:
            self.db.rollback()

            self.audit.log_rbac_error(
                actor_user_id=actor_user_id,
                action="rbac.role_permission.remove",
                entity_type="role_permission",
                role_id=role_id,
                permission_id=permission_id,
                message=f"Unexpected error: {str(exc)}",
            )
            raise