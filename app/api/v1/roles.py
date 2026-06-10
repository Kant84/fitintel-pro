# app/api/v1/roles.py

# Импорт UUID для работы с UUID-идентификаторами.
from uuid import UUID

# Импорт компонентов FastAPI.
from fastapi import APIRouter, Depends, HTTPException

# Импорт select для SQLAlchemy-запросов.
from sqlalchemy import select

# Импорт Session и selectinload для загрузки связанных объектов.
from sqlalchemy.orm import Session, selectinload

# Импорт зависимости проверки прав доступа.
from app.api.dependencies import require_permission

# Импорт зависимости получения сессии БД.
from app.db.session import get_db

# Импорт моделей.
from app.models.role import Role
from app.models.role_permission import RolePermission

# Импорт схем ролей.
from app.schemas.role import RoleRead, RoleUpdate

# Импорт схем permissions.
from app.schemas.permission import PermissionRead

# Импорт схем для операций роль-право.
from app.schemas.role_permission import (
    RolePermissionCreate,
    RolePermissionActionResult,
)

# Импорт сервисов.
from app.services.role_permission_service import RolePermissionService
from app.services.role_service import RoleService


# Создаём роутер ролей.
router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleRead])
def get_roles(
    db: Session = Depends(get_db),
):
    """
    Возвращает список всех ролей вместе с permissions.
    """

    # Готовим SQLAlchemy-запрос с подгрузкой permissions роли.
    stmt = (
        select(Role)
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
        .order_by(Role.code)
    )

    # Выполняем запрос.
    roles = db.execute(stmt).scalars().unique().all()

    # Возвращаем список ролей.
    return roles


@router.get("/{role_id}", response_model=RoleRead)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Возвращает одну роль по её ID вместе с permissions.
    """

    # Формируем запрос одной роли.
    stmt = (
        select(Role)
        .where(Role.id == role_id)
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
    )

    # Выполняем запрос.
    role = db.execute(stmt).scalar_one_or_none()

    # Если роль не найдена — отдаём 404.
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    # Возвращаем найденную роль.
    return role


@router.get("/{role_id}/permissions", response_model=list[PermissionRead])
def get_role_permissions(
    role_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Возвращает список permissions конкретной роли.
    """

    # Загружаем роль вместе с permissions.
    stmt = (
        select(Role)
        .where(Role.id == role_id)
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
    )

    # Выполняем запрос.
    role = db.execute(stmt).scalar_one_or_none()

    # Если роль не найдена — отдаём 404.
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    # Собираем permissions из связующей таблицы.
    permissions = [
        item.permission
        for item in role.role_permissions
        if item.permission is not None
    ]

    # Возвращаем список permissions.
    return permissions


@router.post(
    "/{role_id}/permissions",
    response_model=RolePermissionActionResult,
    status_code=201,
)
def add_permission_to_role(
    role_id: UUID,
    payload: RolePermissionCreate,
    current_user=Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
):
    """
    Добавляет permission к роли.

    Важно:
    - actor_user_id обязательно передаётся в сервис
    - аудит пишется внутри сервиса
    """

    # Создаём сервис для связи role-permission.
    service = RolePermissionService(db)

    try:
        # Вызываем сервис и передаём ID текущего пользователя.
        created_link = service.add_permission_to_role(
            actor_user_id=current_user.id,
            role_id=role_id,
            permission_id=payload.permission_id,
        )

    except HTTPException:
        # Если сервис уже подготовил HTTPException — просто пробрасываем.
        raise

    except ValueError as exc:
        # Совместимость со старой логикой сервиса.
        message = str(exc)

        if message == "Role not found":
            raise HTTPException(status_code=404, detail=message)

        if message == "Permission not found":
            raise HTTPException(status_code=404, detail=message)

        if message == "Permission already assigned to role":
            raise HTTPException(status_code=409, detail=message)

        raise HTTPException(status_code=400, detail=message)

    # Возвращаем стандартный результат.
    return RolePermissionActionResult(
        status="created",
        role_id=created_link.role_id,
        permission_id=created_link.permission_id,
    )


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=RolePermissionActionResult,
)
def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    current_user=Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
):
    """
    Удаляет permission у роли.

    Важно:
    - actor_user_id обязательно передаётся в сервис
    - аудит пишется внутри сервиса
    """

    # Создаём сервис удаления permission у роли.
    service = RolePermissionService(db)

    try:
        # Вызываем сервис и передаём ID текущего пользователя.
        service.remove_permission_from_role(
            actor_user_id=current_user.id,
            role_id=role_id,
            permission_id=permission_id,
        )

    except HTTPException:
        # Если сервис уже вернул корректную HTTPException — пробрасываем дальше.
        raise

    except ValueError as exc:
        # Совместимость со старой логикой.
        message = str(exc)

        if message == "Role not found":
            raise HTTPException(status_code=404, detail=message)

        if message == "Permission not found":
            raise HTTPException(status_code=404, detail=message)

        if message == "Role permission link not found":
            raise HTTPException(status_code=404, detail=message)

        raise HTTPException(status_code=400, detail=message)

    # Возвращаем результат удаления.
    return RolePermissionActionResult(
        status="deleted",
        role_id=role_id,
        permission_id=permission_id,
    )


@router.patch("/{role_id}", response_model=RoleRead)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    current_user=Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
):
    """
    Обновляет роль через новый RoleService с guard + audit.
    """

    # Создаём сервис ролей.
    service = RoleService(db)

    try:
        # Вызываем обновление роли и ОБЯЗАТЕЛЬНО передаём actor_user_id.
        updated_role = service.update_role(
            role_id=role_id,
            actor_user_id=current_user.id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            is_system=payload.is_system,
        )

    except HTTPException:
        # Если сервис уже выбросил HTTPException, просто отдаём её дальше.
        raise

    except ValueError as exc:
        # Совместимость со старой схемой ошибок.
        message = str(exc)

        if message == "Role not found":
            raise HTTPException(status_code=404, detail=message)

        raise HTTPException(status_code=400, detail=message)

    # Возвращаем обновлённую роль.
    return updated_role


@router.delete("/{role_id}")
def delete_role(
    role_id: UUID,
    current_user=Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
):
    """
    Удаляет роль через новый RoleService с guard + audit.
    """

    # Создаём сервис ролей.
    service = RoleService(db)

    try:
        # Вызываем удаление роли и ОБЯЗАТЕЛЬНО передаём actor_user_id.
        service.delete_role(
            role_id=role_id,
            actor_user_id=current_user.id,
        )

    except HTTPException:
        # Если сервис уже выбросил HTTPException — пробрасываем дальше.
        raise

    except ValueError as exc:
        # Совместимость со старой логикой ошибок.
        message = str(exc)

        if message == "Role not found":
            raise HTTPException(status_code=404, detail=message)

        raise HTTPException(status_code=400, detail=message)

    # Возвращаем стандартный JSON-ответ.
    return {
        "status": "deleted",
        "role_id": role_id,
    }