# app/services/role_service.py

# Импорт UUID для типизации идентификаторов.
from uuid import UUID

# Импорт Optional для необязательных параметров.
from typing import Optional

# Импорт HTTPException для явного проброса HTTP-ошибок дальше без искажения.
from fastapi import HTTPException

# Импорт Session для работы с сессией SQLAlchemy.
from sqlalchemy.orm import Session

# Импорт модели Role.
from app.models.role import Role

# Импорт сервиса защитных правил RBAC.
from app.services.rbac_guard import RBACGuardService

# Импорт сервиса аудита.
from app.services.audit_service import AuditService


class RoleService:
    """
    Сервис для безопасного обновления и удаления ролей.

    Что делает этот сервис:
    1. Ищет роль в базе.
    2. Проверяет защитные RBAC-правила через RBACGuardService.
    3. Выполняет update/delete.
    4. Пишет аудит в audit_logs:
       - success
       - denied
       - error
    """

    def __init__(self, db: Session):
        # Сохраняем сессию БД.
        self.db = db

        # Инициализируем guard-сервис для проверок безопасности.
        self.guard = RBACGuardService(db)

        # Инициализируем audit-сервис для записи событий.
        self.audit = AuditService(db)

    def delete_role(self, role_id: UUID, actor_user_id: UUID) -> None:
        """
        Безопасно удаляет роль.

        Логика:
        1. Ищем роль по ID.
        2. Если роль не найдена — пишем audit error и возвращаем 404.
        3. Проверяем через RBACGuardService, можно ли удалять роль.
        4. Если guard запретил — пишем audit denied и отдаём ошибку.
        5. Если удаление успешно — пишем audit success.
        6. Если произошла неожиданная ошибка — делаем rollback и пишем audit error.
        """

        # 1. Ищем роль по id.
        role = self.db.get(Role, role_id)

        # 2. Если роль не найдена — логируем это в аудит и отдаём 404.
        if role is None:
            self.audit.log(
                action="rbac.role.delete",
                status="error",
                message="Role not found",
                actor_user_id=actor_user_id,
                role_id=role_id,
            )
            raise HTTPException(status_code=404, detail="Role not found")

        # 3. Проверяем защитные правила удаления.
        try:
            self.guard.check_can_delete_role(role)

        # Если guard уже выбросил HTTPException — логируем denied и пробрасываем дальше.
        except HTTPException as exc:
            self.audit.log(
                action="rbac.role.delete",
                status="denied",
                message=exc.detail if hasattr(exc, "detail") else str(exc),
                actor_user_id=actor_user_id,
                role_id=role.id,
            )
            raise

        # Если guard выбросил обычное исключение — тоже считаем это denied.
        except Exception as exc:
            self.audit.log(
                action="rbac.role.delete",
                status="denied",
                message=str(exc),
                actor_user_id=actor_user_id,
                role_id=role.id,
            )
            raise HTTPException(status_code=403, detail=str(exc))

        # 4. Если проверки пройдены — удаляем роль.
        try:
            # Удаляем объект роли.
            self.db.delete(role)

            # Подтверждаем транзакцию.
            self.db.commit()

            # Пишем успешный аудит.
            self.audit.log(
                action="rbac.role.deleted",
                status="success",
                message="Role deleted",
                actor_user_id=actor_user_id,
                role_id=role.id,
            )

        # Любая неожиданная ошибка удаления.
        except HTTPException:
            # HTTPException не преобразуем, просто пробрасываем дальше.
            raise

        except Exception as exc:
            # Откатываем транзакцию удаления.
            self.db.rollback()

            # Пишем audit error.
            self.audit.log(
                action="rbac.role.delete",
                status="error",
                message=str(exc),
                actor_user_id=actor_user_id,
                role_id=role.id,
            )

            # Отдаём 500 как внутреннюю ошибку сервера.
            raise HTTPException(status_code=500, detail="Unexpected error while deleting role")

    def update_role(
        self,
        role_id: UUID,
        actor_user_id: UUID,
        code: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_system: Optional[bool] = None,
    ) -> Role:
        """
        Безопасно обновляет роль.

        Логика:
        1. Ищем роль.
        2. Если не найдена — audit error + 404.
        3. Проверяем RBAC Guard:
           - нельзя опасно менять критичные роли
           - нельзя менять code у admin / owner / device
           - нельзя менять is_system у критичных ролей
        4. Если guard запретил — audit denied.
        5. Обновляем только те поля, которые реально переданы.
        6. Сохраняем изменения.
        7. Пишем audit success.
        8. При неожиданных ошибках — rollback + audit error.
        """

        # 1. Ищем роль по ID.
        role = self.db.get(Role, role_id)

        # 2. Если не нашли — пишем аудит и отдаём 404.
        if role is None:
            self.audit.log(
                action="rbac.role.update",
                status="error",
                message="Role not found",
                actor_user_id=actor_user_id,
                role_id=role_id,
            )
            raise HTTPException(status_code=404, detail="Role not found")

        # 3. Проверяем защитные правила перед изменением.
        try:
            self.guard.check_can_modify_role(
                role=role,
                new_code=code,
                new_is_system=is_system,
            )

        # Если guard вернул HTTPException — логируем denied и пробрасываем дальше.
        except HTTPException as exc:
            self.audit.log(
                action="rbac.role.update",
                status="denied",
                message=exc.detail if hasattr(exc, "detail") else str(exc),
                actor_user_id=actor_user_id,
                role_id=role.id,
            )
            raise

        # Если guard выбросил обычную ошибку — тоже трактуем как denied.
        except Exception as exc:
            self.audit.log(
                action="rbac.role.update",
                status="denied",
                message=str(exc),
                actor_user_id=actor_user_id,
                role_id=role.id,
            )
            raise HTTPException(status_code=403, detail=str(exc))

        # 4. Выполняем обновление.
        try:
            # Обновляем code только если поле реально передано.
            if code is not None:
                role.code = code

            # Обновляем name только если поле реально передано.
            if name is not None:
                role.name = name

            # Обновляем description только если поле реально передано.
            if description is not None:
                role.description = description

            # Обновляем is_system только если поле реально передано.
            if is_system is not None:
                role.is_system = is_system

            # Подтверждаем изменения.
            self.db.commit()

            # Обновляем объект роли из БД.
            self.db.refresh(role)

            # Пишем успешный аудит.
            self.audit.log(
                action="rbac.role.updated",
                status="success",
                message="Role updated",
                actor_user_id=actor_user_id,
                role_id=role.id,
            )

            # Возвращаем обновлённую роль.
            return role

        # HTTPException пробрасываем как есть.
        except HTTPException:
            raise

        # Любая неожиданная ошибка при обновлении.
        except Exception as exc:
            # Откатываем изменения.
            self.db.rollback()

            # Пишем audit error.
            self.audit.log(
                action="rbac.role.update",
                status="error",
                message=str(exc),
                actor_user_id=actor_user_id,
                role_id=role.id,
            )

            # Отдаём внутреннюю ошибку.
            raise HTTPException(status_code=500, detail="Unexpected error while updating role")