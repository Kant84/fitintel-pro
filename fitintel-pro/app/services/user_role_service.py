# app/services/user_role_service.py

# импорт UUID для типизации идентификаторов
from uuid import UUID

# импорт HTTPException и status для API-ошибок
from fastapi import HTTPException, status

# импорт select для SQLAlchemy-запросов
from sqlalchemy import select

# импорт Session для SQLAlchemy-сессии
from sqlalchemy.orm import Session

# импорт ORM-моделей
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole

# импорт guard-сервиса для защитных правил
from app.services.rbac_guard import RBACGuardService

# импорт сервиса аудита
from app.services.audit_service import AuditService


class UserRoleService:
    """
    Сервис назначения и снятия ролей у пользователей.

    Что делает:
    - назначает роль пользователю
    - снимает роль у пользователя
    - применяет guard-проверки
    - пишет аудит
    - проверяет целостность RBAC после изменения
    """

    def __init__(self, db: Session):
        # сохраняем текущую сессию БД
        self.db = db

        # создаём сервис защитных RBAC-правил
        self.guard = RBACGuardService(db)

        # создаём сервис аудита
        self.audit = AuditService(db)

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    def _get_user_or_404(self, user_id: UUID) -> User:
        # получаем пользователя по id
        user = self.db.get(User, user_id)

        # если пользователь не найден — возвращаем 404
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # возвращаем найденного пользователя
        return user

    def _get_role_or_404(self, role_id: UUID) -> Role:
        # получаем роль по id
        role = self.db.get(Role, role_id)

        # если роль не найдена — возвращаем 404
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )

        # возвращаем найденную роль
        return role

    def _get_user_role_link(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> UserRole | None:
        # формируем запрос связи user-role
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )

        # выполняем запрос и возвращаем связь или None
        return self.db.execute(stmt).scalar_one_or_none()

    # ============================================================
    # НАЗНАЧЕНИЕ РОЛИ
    # ============================================================

    def add_role_to_user(
        self,
        actor_user_id: UUID,
        user_id: UUID,
        role_id: UUID,
    ) -> None:
        # оборачиваем операцию в try/except для корректного аудита и rollback
        try:
            # проверяем, что пользователь существует
            self._get_user_or_404(user_id)

            # получаем роль или возвращаем 404
            role = self._get_role_or_404(role_id)

            # проверяем, нет ли уже такой связи user-role
            existing_link = self._get_user_role_link(
                user_id=user_id,
                role_id=role_id,
            )

            # если связь уже существует — возвращаем 409
            if existing_link is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Role already assigned to user",
                )

            # guard-проверка перед назначением роли
            self.guard.check_can_assign_role(
                actor_user_id=actor_user_id,
                role=role,
            )

            # создаём новую связь пользователя и роли
            link = UserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_by_user_id=actor_user_id,
            )

            # добавляем связь в сессию
            self.db.add(link)

            # выполняем flush, чтобы изменения попали в текущую транзакцию,
            # но ещё не были окончательно зафиксированы
            self.db.flush()

            # проверяем целостность RBAC после изменения, но до commit
            self.guard.check_rbac_matrix_health()

            # пишем успешный аудит назначения роли
            self.audit.log(
                action="rbac.role.assigned",
                status="success",
                actor_user_id=actor_user_id,
                role_id=role_id,
                target_user_id=user_id,
                message="Role assigned",
                after_data={
                    "target_user_id": str(user_id),
                    "role_id": str(role_id),
                    "role_code": role.code,
                },
            )

            # фиксируем транзакцию
            self.db.commit()

        except HTTPException as exc:
            # откатываем транзакцию
            self.db.rollback()

            # если это запрет доступа — пишем denied
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                self.audit.log(
                    action="rbac.role.assign",
                    status="denied",
                    actor_user_id=actor_user_id,
                    role_id=role_id,
                    target_user_id=user_id,
                    message=exc.detail,
                )
            else:
                # для остальных HTTP-ошибок пишем error
                self.audit.log(
                    action="rbac.role.assign",
                    status="error",
                    actor_user_id=actor_user_id,
                    role_id=role_id,
                    target_user_id=user_id,
                    message=str(exc.detail),
                )

            # пробрасываем ошибку дальше
            raise

        except Exception as exc:
            # откатываем транзакцию при любой неожиданной ошибке
            self.db.rollback()

            # пишем error-аудит
            self.audit.log(
                action="rbac.role.assign",
                status="error",
                actor_user_id=actor_user_id,
                role_id=role_id,
                target_user_id=user_id,
                message=str(exc),
            )

            # пробрасываем ошибку дальше
            raise

    # ============================================================
    # СНЯТИЕ РОЛИ
    # ============================================================

    def remove_role_from_user(
        self,
        actor_user_id: UUID,
        user_id: UUID,
        role_id: UUID,
    ) -> None:
        # оборачиваем операцию в try/except для корректного аудита и rollback
        try:
            # проверяем, что пользователь существует
            self._get_user_or_404(user_id)

            # получаем роль или возвращаем 404
            role = self._get_role_or_404(role_id)

            # получаем связь user-role
            link = self._get_user_role_link(
                user_id=user_id,
                role_id=role_id,
            )

            # если связи нет — возвращаем 404
            if link is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User role link not found",
                )

            # guard-проверка перед снятием роли
            self.guard.check_can_revoke_role(
                user_id=user_id,
                role=role,
            )

            # удаляем связь из сессии
            self.db.delete(link)

            # выполняем flush, чтобы проверить состояние RBAC до commit
            self.db.flush()

            # проверяем целостность RBAC после изменения
            self.guard.check_rbac_matrix_health()

            # пишем успешный аудит снятия роли
            self.audit.log(
                action="rbac.role.revoked",
                status="success",
                actor_user_id=actor_user_id,
                role_id=role_id,
                target_user_id=user_id,
                message="Role revoked",
                before_data={
                    "target_user_id": str(user_id),
                    "role_id": str(role_id),
                    "role_code": role.code,
                },
            )

            # фиксируем транзакцию
            self.db.commit()

        except HTTPException as exc:
            # откатываем транзакцию
            self.db.rollback()

            # если это запрет доступа — пишем denied
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                self.audit.log(
                    action="rbac.role.revoke",
                    status="denied",
                    actor_user_id=actor_user_id,
                    role_id=role_id,
                    target_user_id=user_id,
                    message=exc.detail,
                )
            else:
                # для остальных HTTP-ошибок пишем error
                self.audit.log(
                    action="rbac.role.revoke",
                    status="error",
                    actor_user_id=actor_user_id,
                    role_id=role_id,
                    target_user_id=user_id,
                    message=str(exc.detail),
                )

            # пробрасываем ошибку дальше
            raise

        except Exception as exc:
            # откатываем транзакцию при неожиданной ошибке
            self.db.rollback()

            # пишем error-аудит
            self.audit.log(
                action="rbac.role.revoke",
                status="error",
                actor_user_id=actor_user_id,
                role_id=role_id,
                target_user_id=user_id,
                message=str(exc),
            )

            # пробрасываем ошибку дальше
            raise