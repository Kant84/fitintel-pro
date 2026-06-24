# app/api/v1/users.py

# Импорт UUID для типизации идентификаторов пользователей из URL.
from uuid import UUID

# Импорт основных инструментов FastAPI:
# APIRouter - создаёт роутер,
# Depends - подключает зависимости,
# Query - описывает query-параметры,
# HTTPException - возвращает HTTP-ошибки.
from fastapi import APIRouter, Depends, Query, status

# Импорт Session SQLAlchemy для работы с базой данных.
from sqlalchemy.orm import Session
# Импорт модели пользователя для типизации текущего пользователя.
from sqlalchemy import select


from app.models.role import Role

# Импорт зависимостей безопасности:
# get_current_active_user - получить текущего активного пользователя,
# require_permission - проверить наличие нужного permission.
from app.api.dependencies import get_current_active_user, require_permission

# Импорт функции получения сессии базы данных.
from app.db.session import get_db

# Импорт схем пользователей.
from app.schemas.user import (
    UserCreateRequest,      # Схема создания пользователя
    UserListResponse,       # Схема ответа со списком пользователей
    UserResponse,           # Схема ответа одного пользователя
    UserRoleAssignRequest,  # Схема назначения роли пользователю
    UserRoleRevokeRequest,  # Схема снятия роли у пользователя
    UserUpdateRequest,      # Схема обновления пользователя администратором
    SelfUpdateRequest,      # Схема self-service обновления своего профиля
)

# Импорт схем аутентификации и парольных операций.
from app.schemas.auth import (
    ChangePasswordRequest,      # Схема смены своего пароля
    AdminResetPasswordRequest,  # Схема административного сброса пароля
)

# Импорт RBAC-схем для диагностических endpoints.
from app.schemas.rbac import (
    PermissionShortRead,    # Короткая схема права
    RoleShortRead,          # Короткая схема роли
    UserPermissionsRead,    # Ответ со списком прав пользователя
    UserRolesRead,          # Ответ со списком ролей пользователя
)

# Импорт сервиса пользователей.
from app.services.user_service import UserService

from app.services.user_role_service import UserRoleService

# Импорт сервиса аутентификации для операций с паролями.
from app.services.auth_service import AuthService

# Импорт RBAC-сервиса для получения ролей и прав пользователя.
from app.services.rbac_service import RBACService


# Создаём роутер users.
# Все пути этого файла будут начинаться с /users
# и попадут в группу Users в Swagger.
router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================
# SELF-SERVICE: ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ
# ============================================================

# ============================================================
# Получить текущего пользователя
# ============================================================
@router.get("/me", response_model=UserResponse)
def read_me(
    # Получаем текущего авторизованного и активного пользователя.
    current_user=Depends(get_current_active_user),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Возвращаем текущего пользователя в формате UserResponse.
    return user_service.build_user_response(current_user)


# ============================================================
# Обновить свой профиль
# ============================================================
@router.patch("/me/update", response_model=UserResponse)
def update_me(
    # Тело запроса self-service.
    payload: SelfUpdateRequest,

    # Получаем текущего авторизованного и активного пользователя.
    current_user=Depends(get_current_active_user),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Обновляем только свой профиль через отдельный self-service метод.
    user = user_service.update_own_profile(
        user=current_user,
        username=payload.username,
        email=payload.email,
    )

    # Перечитываем пользователя из БД уже с ролями и правами.
    updated_user = user_service.get_user_by_id(str(user.id))

    # Возвращаем готовый ответ.
    return user_service.build_user_response(updated_user)


# ============================================================
# Сменить свой пароль
# ============================================================
@router.post("/me/change-password")
def change_my_password(
    # Тело запроса на смену своего пароля.
    payload: ChangePasswordRequest,

    # Получаем текущего активного пользователя.
    current_user=Depends(get_current_active_user),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис аутентификации.
    auth_service = AuthService(db)

    # Меняем пароль через отдельную безопасную операцию.
    auth_service.change_own_password(
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )

    # Возвращаем компактный ответ.
    return {
        "status": "success",
        "message": "Пароль успешно изменён",
    }


# ============================================================
# ADMIN: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ============================================================

# ============================================================
# Получить список пользователей
# ============================================================
@router.get("/", response_model=UserListResponse)
def list_users(
    # Смещение для пагинации.
    offset: int = Query(default=0, ge=0),

    # Максимальное количество записей.
    limit: int = Query(default=100, ge=1, le=200),

    # Фильтрация по роли.
    role: str | None = Query(default=None),

    # Требуем право на чтение пользователей.
    current_user=Depends(require_permission("users.read")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Получаем список пользователей.
    users = user_service.list_users(offset=offset, limit=limit, role=role)

    # Возвращаем готовый ответ.
    return user_service.build_user_list_response(users)


# ============================================================
# Получить пользователя по UUID
# ============================================================
@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    # UUID пользователя из URL.
    user_id: UUID,

    # Требуем право на чтение пользователей.
    current_user=Depends(require_permission("users.read")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Получаем пользователя по id.
    user = user_service.get_user_by_id(str(user_id))

    # Возвращаем пользователя в нужной схеме.
    return user_service.build_user_response(user)


# ============================================================
# Создать пользователя
# ============================================================
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    # Тело запроса.
    payload: UserCreateRequest,

    # Требуем право на создание пользователей.
    current_user=Depends(require_permission("users.create")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Создаём нового пользователя.
    user = user_service.create_user(
        email=payload.email,
        username=payload.username,
        password=payload.password,
        is_active=payload.is_active,
    )

    # Перечитываем пользователя из БД вместе с ролями и правами.
    created_user = user_service.get_user_by_id(str(user.id))

    # Возвращаем готовый ответ.
    return user_service.build_user_response(created_user)


# ============================================================
# Обновить пользователя администратором
# ============================================================
@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    # UUID пользователя из URL.
    user_id: UUID,

    # Тело запроса.
    payload: UserUpdateRequest,

    # Требуем право на изменение пользователей.
    current_user=Depends(require_permission("users.update")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Обновляем пользователя.
    # Здесь НЕ меняем пароль.
    user = user_service.update_user(
        user_id=str(user_id),
        email=payload.email,
        username=payload.username,
        is_active=payload.is_active,
    )

    # Перечитываем пользователя вместе с ролями и правами.
    updated_user = user_service.get_user_by_id(str(user.id))

    # Возвращаем ответ.
    return user_service.build_user_response(updated_user)


# ============================================================
# Деактивировать пользователя
# ============================================================
@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    # UUID пользователя из URL.
    user_id: UUID,

    # Требуем право на изменение пользователей.
    current_user=Depends(require_permission("users.update")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Деактивируем пользователя.
    user = user_service.deactivate_user(str(user_id))

    # Перечитываем пользователя из БД.
    updated_user = user_service.get_user_by_id(str(user.id))

    # Возвращаем ответ.
    return user_service.build_user_response(updated_user)


# ============================================================
# Административный сброс пароля пользователя
# ============================================================
@router.post("/{user_id}/reset-password")
def reset_user_password(
    # UUID пользователя из URL.
    user_id: UUID,

    # Тело запроса.
    payload: AdminResetPasswordRequest,

    # Требуем право на изменение пользователей.
    # Позже можно заменить на отдельный permission, например users.password.reset
    current_user=Depends(require_permission("users.update")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём сервис пользователей.
    user_service = UserService(db)

    # Создаём сервис аутентификации.
    auth_service = AuthService(db)

    # Получаем целевого пользователя.
    target_user = user_service.get_user_by_id(str(user_id))

    # Выполняем административный сброс пароля.
    auth_service.admin_reset_password(
        actor_user=current_user,
        target_user=target_user,
        new_password=payload.new_password,
        force_password_change=payload.force_password_change,
    )

    # Возвращаем компактный ответ.
    return {
        "status": "success",
        "message": "Пароль пользователя успешно сброшен",
        "target_user_id": str(target_user.id),
        "force_password_change": payload.force_password_change,
    }


# ============================================================
# RBAC: НАЗНАЧЕНИЕ И СНЯТИЕ РОЛЕЙ
# ============================================================

# ============================================================
# Назначить роль пользователю
# ============================================================
@router.post("/{user_id}/roles/assign", response_model=UserResponse)
def assign_role(
    user_id: UUID,
    payload: UserRoleAssignRequest,
    current_user=Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
):
    user_service = UserService(db)
    user_role_service = UserRoleService(db)

    user = user_service.get_user_by_id(str(user_id))

    stmt = select(Role).where(Role.code == payload.role_code)
    role = db.execute(stmt).scalar_one_or_none()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    user_role_service.add_role_to_user(
        actor_user_id=current_user.id,
        user_id=user.id,
        role_id=role.id,
    )

    updated_user = user_service.get_user_by_id(str(user.id))
    return user_service.build_user_response(updated_user)

# ============================================================
# Снять роль у пользователя
# ============================================================
@router.post("/{user_id}/roles/revoke", response_model=UserResponse)
def revoke_role(
    user_id: UUID,
    payload: UserRoleRevokeRequest,
    current_user=Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
):
    user_service = UserService(db)
    user_role_service = UserRoleService(db)

    user = user_service.get_user_by_id(str(user_id))

    stmt = select(Role).where(Role.code == payload.role_code)
    role = db.execute(stmt).scalar_one_or_none()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    user_role_service.remove_role_from_user(
        actor_user_id=current_user.id,
        user_id=user.id,
        role_id=role.id,
    )

    updated_user = user_service.get_user_by_id(str(user.id))
    return user_service.build_user_response(updated_user)

# ============================================================
# RBAC: ЧТЕНИЕ РОЛЕЙ И ПРАВ ПОЛЬЗОВАТЕЛЯ
# ============================================================

# ============================================================
# Получить список ролей конкретного пользователя
# ============================================================

# маршрут удаления пользователя
@router.delete("/{user_id}")
def delete_user(
    user_id: UUID,
    current_user=Depends(require_permission("users.delete")),
    db: Session = Depends(get_db),
):
    """Удаление пользователя"""
    user_service = UserService(db)
    user = user_service.get_user_by_id(str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_service.delete_user(user)
    return {"message": "Пользователь удалён"}


@router.get("/{user_id}/roles", response_model=UserRolesRead)
def get_user_roles(
    # UUID пользователя из URL.
    user_id: UUID,

    # Требуем право чтения пользователей.
    current_user=Depends(require_permission("users.read")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём RBAC-сервис.
    service = RBACService(db)

    # Получаем роли пользователя.
    roles = service.get_user_roles(user_id)

    # Собираем и возвращаем компактный ответ.
    return UserRolesRead(
        user_id=user_id,
        roles=[
            RoleShortRead(
                code=role.code,
                name=role.name,
            )
            for role in roles
        ],
    )


# ============================================================
# Получить итоговые права конкретного пользователя
# ============================================================
@router.get("/{user_id}/permissions", response_model=UserPermissionsRead)
def get_user_permissions(
    # UUID пользователя из URL.
    user_id: UUID,

    # Требуем право чтения пользователей.
    current_user=Depends(require_permission("users.read")),

    # Получаем сессию базы данных.
    db: Session = Depends(get_db),
):
    # Создаём RBAC-сервис.
    service = RBACService(db)

    # Получаем итоговые права пользователя.
    permissions = service.get_user_permissions(user_id)

    # Собираем и возвращаем компактный ответ.
    return UserPermissionsRead(
        user_id=user_id,
        permissions=[
            PermissionShortRead(
                code=permission.code,
                name=permission.name,
            )
            for permission in permissions
        ],
    )
