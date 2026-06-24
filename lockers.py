from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Locker, Client, AuditLog
from app.schemas import (
    LockerCreate, LockerUpdate, LockerResponse, LockerStatusResponse,
    LockerOccupyRequest, AuditLogCreate, ErrorResponse
)
from app.schemas.enums import LockerStatus
from app.core.auth import get_current_user, require_permission
from app.core.audit import log_action

router = APIRouter(prefix="/lockers", tags=["Шкафчики (E4)"])


@router.post("", response_model=LockerResponse, status_code=status.HTTP_201_CREATED)
@require_permission("lockers.create")
async def create_locker(
    locker: LockerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.8 — Создание шкафчика
    Предусловия: Админ авторизован, право lockers.create
    """
    # Проверка уникальности номера
    existing = db.query(Locker).filter(Locker.number == locker.number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": f"Шкафчик с номером «{locker.number}» уже существует",
                "code": "LOCKER_DUPLICATE",
                "field": "number",
                "suggestion": "Выберите другой номер шкафчика"
            }
        )

    db_locker = Locker(
        number=locker.number,
        zone=locker.zone,
        size=locker.size,
        status=LockerStatus.FREE,
        notes=locker.notes
    )
    db.add(db_locker)
    db.commit()
    db.refresh(db_locker)

    # Аудит
    log_action(
        db=db,
        user_id=current_user.id,
        action="locker_created",
        entity_type="locker",
        entity_id=db_locker.id,
        details={"number": locker.number, "zone": locker.zone}
    )

    return db_locker


@router.get("", response_model=List[LockerResponse])
@require_permission("lockers.read")
async def list_lockers(
    zone: Optional[str] = None,
    status: Optional[LockerStatus] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.8 — Список шкафчиков с фильтрами
    """
    query = db.query(Locker)

    if zone:
        query = query.filter(Locker.zone == zone)
    if status:
        query = query.filter(Locker.status == status)

    lockers = query.order_by(Locker.number).all()
    return lockers


@router.get("/status", response_model=LockerStatusResponse)
@require_permission("lockers.read")
async def get_lockers_status(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.8 — Статистика по шкафчикам
    """
    total = db.query(Locker).count()
    free = db.query(Locker).filter(Locker.status == LockerStatus.FREE).count()
    occupied = db.query(Locker).filter(Locker.status == LockerStatus.OCCUPIED).count()
    reserved = db.query(Locker).filter(Locker.status == LockerStatus.RESERVED).count()
    out_of_order = db.query(Locker).filter(Locker.status == LockerStatus.OUT_OF_ORDER).count()

    # По зонам
    zones = db.query(Locker.zone).distinct().all()
    by_zone = {}
    for zone_tuple in zones:
        zone_name = zone_tuple[0] or "default"
        by_zone[zone_name] = {
            "total": db.query(Locker).filter(Locker.zone == zone_name).count(),
            "free": db.query(Locker).filter(Locker.zone == zone_name, Locker.status == LockerStatus.FREE).count(),
            "occupied": db.query(Locker).filter(Locker.zone == zone_name, Locker.status == LockerStatus.OCCUPIED).count()
        }

    return LockerStatusResponse(
        total=total,
        free=free,
        occupied=occupied,
        reserved=reserved,
        out_of_order=out_of_order,
        by_zone=by_zone
    )


@router.get("/{locker_id}", response_model=LockerResponse)
@require_permission("lockers.read")
async def get_locker(
    locker_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.8 — Получить шкафчик по ID
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Шкафчик #{locker_id} не найден",
                "code": "LOCKER_NOT_FOUND",
                "suggestion": "Проверьте ID шкафчика или обновите список"
            }
        )
    return locker


@router.put("/{locker_id}", response_model=LockerResponse)
@require_permission("lockers.update")
async def update_locker(
    locker_id: int,
    locker_update: LockerUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.8 — Обновление шкафчика
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Шкафчик #{locker_id} не найден",
                "code": "LOCKER_NOT_FOUND",
                "suggestion": "Проверьте ID шкафчика"
            }
        )

    # Обновляем поля
    if locker_update.status is not None:
        locker.status = locker_update.status
    if locker_update.client_id is not None:
        # Проверяем существование клиента
        client = db.query(Client).filter(Client.id == locker_update.client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "detail": f"Клиент #{locker_update.client_id} не найден",
                    "code": "CLIENT_NOT_FOUND",
                    "field": "client_id",
                    "suggestion": "Проверьте ID клиента или создайте нового"
                }
            )
        locker.client_id = locker_update.client_id
    if locker_update.occupied_until is not None:
        locker.occupied_until = locker_update.occupied_until
    if locker_update.notes is not None:
        locker.notes = locker_update.notes

    locker.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(locker)

    log_action(
        db=db,
        user_id=current_user.id,
        action="locker_updated",
        entity_type="locker",
        entity_id=locker_id,
        details={"status": locker.status, "client_id": locker.client_id}
    )

    return locker


@router.post("/{locker_id}/occupy", response_model=LockerResponse)
@require_permission("lockers.occupy")
async def occupy_locker(
    locker_id: int,
    occupy_data: LockerOccupyRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.9 — Занять шкафчик
    Предусловия: Шкафчик свободен, клиент существует
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Шкафчик #{locker_id} не найден",
                "code": "LOCKER_NOT_FOUND",
                "suggestion": "Проверьте ID шкафчика"
            }
        )

    # Проверяем, что шкафчик свободен
    if locker.status != LockerStatus.FREE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": f"Шкафчик #{locker.number} уже занят (статус: {locker.status})",
                "code": "LOCKER_OCCUPIED",
                "suggestion": "Выберите другой свободный шкафчик"
            }
        )

    # Проверяем клиента
    client = db.query(Client).filter(Client.id == occupy_data.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Клиент #{occupy_data.client_id} не найден",
                "code": "CLIENT_NOT_FOUND",
                "field": "client_id",
                "suggestion": "Проверьте ID клиента"
            }
        )

    # Занимаем шкафчик
    locker.status = LockerStatus.OCCUPIED
    locker.client_id = occupy_data.client_id
    locker.occupied_at = datetime.utcnow()
    locker.occupied_until = occupy_data.occupied_until
    locker.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(locker)

    log_action(
        db=db,
        user_id=current_user.id,
        action="locker_occupied",
        entity_type="locker",
        entity_id=locker_id,
        details={
            "client_id": occupy_data.client_id,
            "client_name": f"{client.last_name} {client.first_name}",
            "occupied_at": locker.occupied_at.isoformat()
        }
    )

    return locker


@router.post("/{locker_id}/release", response_model=LockerResponse)
@require_permission("lockers.release")
async def release_locker(
    locker_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.10 — Освободить шкафчик
    Предусловия: Шкафчик занят
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Шкафчик #{locker_id} не найден",
                "code": "LOCKER_NOT_FOUND",
                "suggestion": "Проверьте ID шкафчика"
            }
        )

    if locker.status != LockerStatus.OCCUPIED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": f"Шкафчик #{locker.number} не занят (статус: {locker.status})",
                "code": "LOCKER_NOT_OCCUPIED",
                "suggestion": "Шкафчик уже свободен"
            }
        )

    client_id = locker.client_id
    locker.status = LockerStatus.FREE
    locker.client_id = None
    locker.occupied_at = None
    locker.occupied_until = None
    locker.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(locker)

    log_action(
        db=db,
        user_id=current_user.id,
        action="locker_released",
        entity_type="locker",
        entity_id=locker_id,
        details={"previous_client_id": client_id}
    )

    return locker


@router.delete("/{locker_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("lockers.delete")
async def delete_locker(
    locker_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E4.8 — Удалить шкафчик
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Шкафчик #{locker_id} не найден",
                "code": "LOCKER_NOT_FOUND",
                "suggestion": "Проверьте ID шкафчика"
            }
        )

    if locker.status == LockerStatus.OCCUPIED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": f"Нельзя удалить занятый шкафчик #{locker.number}",
                "code": "LOCKER_OCCUPIED",
                "suggestion": "Сначала освободите шкафчик"
            }
        )

    db.delete(locker)
    db.commit()

    log_action(
        db=db,
        user_id=current_user.id,
        action="locker_deleted",
        entity_type="locker",
        entity_id=locker_id,
        details={"number": locker.number}
    )

    return None
