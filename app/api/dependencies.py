# app/api/dependencies.py

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token, oauth2_scheme
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService
from app.services.audit_service import AuditService


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_token(token)
    subject = payload.get("sub")

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="В токене отсутствует subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(subject)
    auth_service = AuthService(db)
    user = auth_service.user_repository.get_by_id_with_roles_permissions(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь из токена не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    if not auth_service.is_user_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    return current_user


def require_roles(*required_roles: str):
    def role_checker(
        current_user=Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        # SuperAdmin bypass
        if getattr(current_user, "username", "").lower() == "superadmin":
            return current_user

        auth_service = AuthService(db)
        raw_roles = auth_service.get_user_roles(current_user)
        user_roles = set()
        for r in raw_roles:
            if hasattr(r, 'code'):
                user_roles.add(r.code)
            else:
                user_roles.add(str(r))

        if not user_roles.intersection(set(required_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно ролей для доступа",
            )

        return current_user

    return role_checker


def require_permissions(*required_permissions: str):
    def permission_checker(
        current_user=Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        # SuperAdmin bypass
        if getattr(current_user, "username", "").lower() == "superadmin":
            return current_user

        rbac = RBACService(db)
        audit = AuditService(db)
        missing_permissions = []

        for permission in required_permissions:
            result = rbac.explain_user_access(
                user_id=current_user.id,
                permission_code=permission,
            )

            if not result["has_access"]:
                missing_permissions.append(permission)
                audit.log(
                    action="access.check.denied",
                    status="denied",
                    actor_user_id=current_user.id,
                    message=result["reason"],
                    after_data=result,
                )

        if missing_permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Нет прав: {', '.join(missing_permissions)}"
            )

        audit.log(
            action="access.check.allowed",
            status="success",
            actor_user_id=current_user.id,
            message="Access granted",
            after_data={"checked_permissions": list(required_permissions)},
        )

        return current_user

    return permission_checker


def require_permission(required_permission: str):
    return require_permissions(required_permission)