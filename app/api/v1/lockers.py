# app/api/v1/lockers.py
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.locker import (
    LockerCreateRequest,
    LockerResponse,
    LockerListResponse,
    LockerAssignRequest,
    LockerBlockRequest,
    LockerStatusResponse,
    LockerOpenResponse,
)
from app.services.locker_service import LockerService

router = APIRouter(prefix="/lockers", tags=["Lockers"])


# ==========================================================
# E11.1: СОЗДАНИЕ ШКАФЧИКА
# ==========================================================

@router.post(
    "",
    response_model=LockerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_locker(
    payload: LockerCreateRequest,
    current_user=Depends(require_permission("lockers.create")),
    db: Session = Depends(get_db),
):
    """Создать шкафчик (E11.1)"""
    service = LockerService(db)
    locker = service.create_locker(
        number=payload.number,
        zone=payload.zone,
        lock_type=payload.lock_type,
        device_id=payload.device_id,
        requires_privilege=payload.requires_privilege,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )
    return LockerResponse.model_validate(locker)


# ==========================================================
# E11.3: СПИСОК ШКАФЧИКОВ
# ==========================================================

@router.get(
    "",
    response_model=LockerListResponse,
    status_code=status.HTTP_200_OK,
)
def list_lockers(
    current_user=Depends(require_permission("lockers.read")),
    db: Session = Depends(get_db),
):
    """Получить список шкафчиков (E11.3)"""
    service = LockerService(db)
    lockers = service.list_lockers()
    return LockerListResponse(
        items=[LockerResponse.model_validate(l) for l in lockers],
        count=len(lockers),
    )


# ==========================================================
# E11.4: ВЫДАЧА ШКАФЧИКА
# ==========================================================

@router.post(
    "/{locker_id}/assign",
    status_code=status.HTTP_200_OK,
)
def assign_locker(
    locker_id: UUID,
    payload: LockerAssignRequest,
    current_user=Depends(require_permission("lockers.update")),
    db: Session = Depends(get_db),
):
    """Выдать шкафчик клиенту (E11.4)"""
    service = LockerService(db)
    session = service.assign_locker(
        locker_id=str(locker_id),
        client_id=str(payload.client_id),
        credential_id=str(payload.credential_id) if payload.credential_id else None,
        actor_user_id=str(current_user.id),
    )
    return {
        "success": True,
        "locker_id": str(locker_id),
        "session_id": str(session.id),
        "client_id": str(session.client_id),
        "status": "OCCUPIED",
    }


# ==========================================================
# E11.6: ОСВОБОЖДЕНИЕ ШКАФЧИКА
# ==========================================================

@router.post(
    "/{locker_id}/release",
    response_model=LockerResponse,
    status_code=status.HTTP_200_OK,
)
def release_locker(
    locker_id: UUID,
    current_user=Depends(require_permission("lockers.update")),
    db: Session = Depends(get_db),
):
    """Освободить шкафчик (E11.6)"""
    service = LockerService(db)
    locker = service.release_locker(
        locker_id=str(locker_id),
        actor_user_id=str(current_user.id),
    )
    return LockerResponse.model_validate(locker)


# ==========================================================
# E11.8: БЛОКИРОВКА ШКАФЧИКА
# ==========================================================

@router.post(
    "/{locker_id}/block",
    response_model=LockerResponse,
    status_code=status.HTTP_200_OK,
)
def block_locker(
    locker_id: UUID,
    payload: LockerBlockRequest,
    current_user=Depends(require_permission("lockers.update")),
    db: Session = Depends(get_db),
):
    """Заблокировать шкафчик (E11.8)"""
    service = LockerService(db)
    locker = service.block_locker(
        locker_id=str(locker_id),
        reason=payload.reason,
        actor_user_id=str(current_user.id),
    )
    return LockerResponse.model_validate(locker)


# ==========================================================
# E11.9: СТАТУС ШКАФЧИКА
# ==========================================================

@router.get(
    "/{locker_id}/status",
    response_model=LockerStatusResponse,
    status_code=status.HTTP_200_OK,
)
def locker_status(
    locker_id: UUID,
    current_user=Depends(require_permission("lockers.read")),
    db: Session = Depends(get_db),
):
    """Получить статус шкафчика (E11.9)"""
    service = LockerService(db)
    result = service.get_locker_status(str(locker_id))
    return LockerStatusResponse(**result)


# ==========================================================
# E11.11: УДАЛЕНИЕ ШКАФЧИКА
# ==========================================================

@router.delete(
    "/{locker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_locker(
    locker_id: UUID,
    current_user=Depends(require_permission("lockers.delete")),
    db: Session = Depends(get_db),
):
    """Удалить шкафчик (E11.11)"""
    service = LockerService(db)
    service.delete_locker(
        locker_id=str(locker_id),
        actor_user_id=str(current_user.id),
    )
    return None


# ==========================================================
# E11.13: ОТКРЫТИЕ ЗАМКА
# ==========================================================

@router.post(
    "/{locker_id}/open",
    status_code=status.HTTP_200_OK,
)
def open_locker(
    locker_id: UUID,
    current_user=Depends(require_permission("lockers.update")),
    db: Session = Depends(get_db),
):
    """Открыть замок шкафчика (E11.13)"""
    service = LockerService(db)
    result = service.open_locker(
        locker_id=str(locker_id),
        actor_user_id=str(current_user.id),
    )
    return result
