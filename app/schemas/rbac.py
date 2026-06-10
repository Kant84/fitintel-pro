# app/schemas/rbac.py

# Импорт UUID для идентификаторов.
from uuid import UUID

# Импорт BaseModel и Field для Pydantic-схем.
from pydantic import BaseModel, Field


# ============================================================
# КОРОТКИЕ СХЕМЫ РОЛЕЙ И ПРАВ
# ============================================================

class RoleShortRead(BaseModel):
    # Код роли.
    code: str

    # Название роли.
    name: str | None = None


class PermissionShortRead(BaseModel):
    # Код права.
    code: str

    # Название права.
    name: str | None = None


# ============================================================
# МАТРИЦА РОЛЕЙ
# ============================================================

class RoleMatrixItem(BaseModel):
    # UUID роли.
    role_id: UUID

    # Код роли.
    role_code: str

    # Название роли.
    role_name: str | None = None

    # Список permission роли.
    permissions: list[PermissionShortRead] = Field(default_factory=list)


# ============================================================
# РОЛИ И ПРАВА ПОЛЬЗОВАТЕЛЯ
# ============================================================

class UserRolesRead(BaseModel):
    # UUID пользователя.
    user_id: UUID

    # Список ролей пользователя.
    roles: list[RoleShortRead] = Field(default_factory=list)


class UserPermissionsRead(BaseModel):
    # UUID пользователя.
    user_id: UUID

    # Список итоговых permission пользователя.
    permissions: list[PermissionShortRead] = Field(default_factory=list)


# ============================================================
# ПРОВЕРКА И EXPLAIN ДОСТУПА
# ============================================================

class AccessCheckRead(BaseModel):
    # UUID пользователя.
    user_id: UUID

    # Код проверяемого permission.
    permission_code: str

    # Есть ли доступ.
    has_access: bool

    # Через какие роли доступ получен.
    granted_via_roles: list[str] = Field(default_factory=list)

    # Все роли пользователя.
    all_roles: list[str] = Field(default_factory=list)

    # Все итоговые permission пользователя.
    all_permissions: list[str] = Field(default_factory=list)


class AccessExplainRead(BaseModel):
    # UUID пользователя.
    user_id: UUID

    # Код проверяемого permission.
    permission_code: str

    # Есть ли доступ.
    has_access: bool

    # Причина результата.
    reason: str

    # Через какие роли доступ получен.
    granted_via_roles: list[str] = Field(default_factory=list)

    # Все роли пользователя.
    all_roles: list[str] = Field(default_factory=list)

    # Все права пользователя.
    all_permissions: list[str] = Field(default_factory=list)

    # Сколько ролей было проверено.
    checked_roles_count: int

    # Сколько итоговых permission было проверено.
    checked_permissions_count: int


# ============================================================
# RBAC SNAPSHOT ПОЛЬЗОВАТЕЛЯ
# ============================================================

class UserRoleItemRead(BaseModel):
    # UUID роли.
    id: UUID

    # Код роли.
    code: str

    # Название роли.
    name: str | None = None

    # Является ли роль системной.
    is_system: bool


class UserPermissionItemRead(BaseModel):
    # UUID permission.
    id: UUID

    # Код permission.
    code: str

    # Название permission.
    name: str | None = None

    # Описание permission.
    description: str | None = None


class UserRBACSnapshotRead(BaseModel):
    # UUID пользователя.
    user_id: UUID

    # Все роли пользователя.
    roles: list[UserRoleItemRead] = Field(default_factory=list)

    # Все итоговые permission пользователя.
    permissions: list[UserPermissionItemRead] = Field(default_factory=list)


# ============================================================
# НЕДОСТАЮЩИЕ ПРАВА
# ============================================================

class MissingPermissionsRead(BaseModel):
    # UUID пользователя.
    user_id: UUID

    # Каких permission не хватает.
    missing_permissions: list[str] = Field(default_factory=list)

    # Какие permission уже есть.
    existing_permissions: list[str] = Field(default_factory=list)

    # Все роли пользователя.
    all_roles: list[str] = Field(default_factory=list)


# ============================================================
# DEBUG ДОСТУПА
# ============================================================

class DebugAccessRead(BaseModel):
    # UUID пользователя.
    user_id: UUID

    # Роли пользователя.
    roles: list[str] = Field(default_factory=list)

    # Итоговые permission пользователя.
    permissions: list[str] = Field(default_factory=list)

    # Недостающие permission.
    missing_permissions: list[str] = Field(default_factory=list)