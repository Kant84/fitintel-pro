# app/api/v1/access.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.access import (
    AccessCheckRequest,
    AccessCheckResponse,
    AccessGrantRequest,
    AccessGrantResponse,
    AccessExitRequest,
    AccessExitResponse,
)
from app.services.access_service import AccessService


router = APIRouter(prefix="/access", tags=["Access Control"])


# ==========================================================
# ПРОВЕРКА ДОСТУПА (БЕЗ СОЗДАНИЯ ПОСЕЩЕНИЯ)
# ==========================================================

@router.post(
    "/check",
    response_model=AccessCheckResponse,
    status_code=status.HTTP_200_OK,
)
def check_access(
    payload: AccessCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Проверить, может ли клиент пройти.
    
    - Не создаёт посещение
    - Только проверка прав
    - Используется для предварительной проверки
    """
    service = AccessService(db)
    return service.check_access(
        credential=payload.credential,
        device_id=payload.device_id,
        zone=payload.zone,
    )


# ==========================================================
# ПРЕДОСТАВЛЕНИЕ ДОСТУПА (ВХОД)
# ==========================================================

@router.post(
    "/grant",
    response_model=AccessGrantResponse,
    status_code=status.HTTP_200_OK,
)
def grant_access(
    payload: AccessGrantRequest,
    current_user=Depends(require_permission("visits.create")),
    db: Session = Depends(get_db),
):
    """
    Предоставить доступ (вход).
    
    - Проверяет права
    - Создаёт посещение
    - Списывает визит
    - Открывает турникет (если настроен)
    """
    service = AccessService(db)
    return service.grant_access(
        credential=payload.credential,
        device_id=payload.device_id,
        zone=payload.zone,
        override=payload.override,
        override_by_user_id=payload.override_by_user_id,
    )


# ==========================================================
# ВЫХОД
# ==========================================================

@router.post(
    "/exit",
    response_model=AccessExitResponse,
    status_code=status.HTTP_200_OK,
)
def exit_access(
    payload: AccessExitRequest,
    current_user=Depends(require_permission("visits.update")),
    db: Session = Depends(get_db),
):
    """
    Зафиксировать выход.
    
    - Завершает активное посещение
    - Рассчитывает длительность
    """
    service = AccessService(db)
    return service.exit_access(
        credential=payload.credential,
        device_id=payload.device_id,
    )


# ==========================================================
# ПРИНУДИТЕЛЬНОЕ ОТКРЫТИЕ (ДЛЯ МЕНЕДЖЕРОВ)
# ==========================================================

@router.post(
    "/override",
    response_model=AccessGrantResponse,
    status_code=status.HTTP_200_OK,
)
def override_access(
    payload: AccessGrantRequest,
    current_user=Depends(require_permission("access.override")),
    db: Session = Depends(get_db),
):
    """
    Принудительное открытие турникета (для менеджеров).
    
    - Игнорирует проверку абонемента
    - Требует специальное право access.override
    """
    service = AccessService(db)
    return service.grant_access(
        credential=payload.credential,
        device_id=payload.device_id,
        zone=payload.zone,
        override=True,
        override_by_user_id=current_user.id,
    )