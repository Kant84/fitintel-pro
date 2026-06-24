# app/api/dependencies.py

# импорт Depends, HTTPException и status из FastAPI
from fastapi import Depends, HTTPException, status

# импорт Session для типизации SQLAlchemy-сессии
from sqlalchemy.orm import Session

# импорт get_db из модуля сессии БД
from app.db.session import get_db

# импорт функций безопасности
from app.core.security import decode_token, oauth2_scheme

# импорт сервиса аутентификации
from app.services.auth_service import AuthService

from app.services.rbac_service import RBACService

from app.services.audit_service import AuditService


# зависимость для получения текущего пользователя по токену
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    # декодируем токен
    payload = decode_token(token)

    # извлекаем subject из payload
    subject = payload.get("sub")

    # если subject отсутствует, возвращаем 401
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="В токене отсутствует subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # в текущем проекте id пользователя — UUID в виде строки
    user_id = str(subject)

    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # ищем пользователя вместе с ролями и правами
    user = auth_service.user_repository.get_by_id_with_roles_permissions(user_id)

    # если пользователь не найден, возвращаем 401
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь из токена не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # возвращаем найденного пользователя
    return user


# зависимость для получения только активного пользователя
def get_current_active_user(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # если пользователь неактивен, возвращаем 403
    if not auth_service.is_user_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    # возвращаем пользователя
    return current_user


# фабрика зависимости для проверки ролей
def require_roles(*required_roles: str):
    # внутренняя функция зависимости
    def role_checker(
        current_user=Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        # создаём сервис аутентификации
        auth_service = AuthService(db)

        # получаем роли пользователя
        raw_roles = auth_service.get_user_roles(current_user)
        # извлекаем code из объектов Role (или строк, если уже строки)
        user_roles = set()
        for r in raw_roles:
            if hasattr(r, 'code'):
                user_roles.add(r.code)
            else:
                user_roles.add(str(r))

        # если пересечения нет, возвращаем 403
        if not user_roles.intersection(set(required_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно ролей для доступа",
            )

        # возвращаем пользователя
        return current_user

    # возвращаем зависимость
    return role_checker


# фабрика зависимости для проверки всех обязательных прав


def require_permissions(*required_permissions: str):

    def permission_checker(
        current_user=Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        rbac = RBACService(db)
        audit = AuditService(db)

        missing_permissions = []

        # проверяем каждое право
        for permission in required_permissions:
            result = rbac.explain_user_access(
                user_id=current_user.id,
                permission_code=permission,
            )

            if not result["has_access"]:
                missing_permissions.append(permission)

                # 🔴 лог отказа
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

        # 🟢 лог успеха
        audit.log(
            action="access.check.allowed",
            status="success",
            actor_user_id=current_user.id,
            message="Access granted",
            after_data={
                "checked_permissions": list(required_permissions)
            },
        )

        return current_user

    return permission_checker

# удобная обёртка для одного права
def require_permission(required_permission: str):
    # используем уже существующую проверку списка прав
    return require_permissions(required_permission)