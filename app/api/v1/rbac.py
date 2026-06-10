# app/api/v1/rbac.py

# Импорт UUID.
from uuid import UUID

# Импорт компонентов FastAPI.
from fastapi import APIRouter, Depends, Query, status

# Импорт Session.
from sqlalchemy.orm import Session

# Импорт зависимостей проекта.
from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db

# Импорт модели пользователя.
from app.models.user import User

# Импорт схем.
from app.schemas.rbac import (
    AccessCheckRead,
    AccessExplainRead,
    DebugAccessRead,
    MissingPermissionsRead,
    PermissionShortRead,
    RoleMatrixItem,
    RoleShortRead,
    UserPermissionsRead,
    UserRBACSnapshotRead,
    UserRolesRead,
)

# Импорт сервисов.
from app.services.rbac_service import RBACService
from app.services.user_role_service import UserRoleService


router = APIRouter(prefix="/rbac", tags=["RBAC"])


@router.post("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_201_CREATED)
def add_role_to_user(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserRoleService(db)

    service.add_role_to_user(
        actor_user_id=current_user.id,
        user_id=user_id,
        role_id=role_id,
    )

    return {
        "status": "success",
        "message": "Role assigned successfully",
        "user_id": str(user_id),
        "role_id": str(role_id),
    }


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserRoleService(db)

    service.remove_role_from_user(
        actor_user_id=current_user.id,
        user_id=user_id,
        role_id=role_id,
    )

    return None


@router.get("/users/{user_id}/roles", response_model=UserRolesRead)
def get_user_roles(
    user_id: UUID,
    current_user=Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)
    roles = service.get_user_roles(user_id=user_id)

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


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsRead)
def get_user_permissions(
    user_id: UUID,
    current_user=Depends(require_permission("permissions.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)
    permissions = service.get_user_permissions(user_id=user_id)

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


@router.get("/roles-matrix", response_model=list[RoleMatrixItem])
def get_roles_matrix(
    current_user=Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)
    roles = service.get_roles_matrix()

    result: list[RoleMatrixItem] = []

    for role in roles:
        permissions = sorted(role.permissions, key=lambda item: item.code)

        result.append(
            RoleMatrixItem(
                role_id=role.id,
                role_code=role.code,
                role_name=role.name,
                permissions=[
                    PermissionShortRead(
                        code=permission.code,
                        name=permission.name,
                    )
                    for permission in permissions
                ],
            )
        )

    return result


@router.get("/check-access", response_model=AccessCheckRead)
def check_user_access(
    user_id: UUID = Query(...),
    permission_code: str = Query(..., min_length=1),
    current_user=Depends(require_permission("permissions.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)

    result = service.check_user_access(
        user_id=user_id,
        permission_code=permission_code,
    )

    return AccessCheckRead(**result)


@router.get("/explain-access", response_model=AccessExplainRead)
def explain_user_access(
    user_id: UUID = Query(...),
    permission_code: str = Query(..., min_length=1),
    current_user=Depends(require_permission("permissions.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)

    result = service.explain_user_access(
        user_id=user_id,
        permission_code=permission_code,
    )

    return AccessExplainRead(**result)


@router.get("/users/{user_id}/snapshot", response_model=UserRBACSnapshotRead)
def get_user_rbac_snapshot(
    user_id: UUID,
    current_user=Depends(require_permission("permissions.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)
    result = service.get_user_rbac_snapshot(user_id=user_id)
    return UserRBACSnapshotRead(**result)


@router.get("/users/{user_id}/missing-permissions", response_model=MissingPermissionsRead)
def get_missing_permissions(
    user_id: UUID,
    required_permissions: list[str] = Query(default_factory=list),
    current_user=Depends(require_permission("permissions.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)

    result = service.get_missing_permissions(
        user_id=user_id,
        required_permissions=required_permissions,
    )

    return MissingPermissionsRead(**result)


@router.get("/debug-access", response_model=DebugAccessRead)
def debug_access(
    user_id: UUID = Query(...),
    required_permissions: list[str] = Query(default_factory=list),
    current_user=Depends(require_permission("permissions.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)

    result = service.debug_access(
        user_id=user_id,
        required_permissions=required_permissions,
    )

    return DebugAccessRead(**result)


@router.get("/health")
def get_rbac_health(
    current_user=Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
):
    service = RBACService(db)
    return service.check_rbac_health()