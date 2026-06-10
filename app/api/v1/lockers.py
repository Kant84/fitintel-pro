"""
Lockers API — управление шкафчиками
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.models.locker import Locker
from app.models.locker_session import LockerSession
router = APIRouter(prefix="/lockers", tags=["lockers"])


@router.post("/release")
def release_locker(
    credential: str,
    device_id: str,
    current_user=Depends(require_permission("lockers.update")),
    db: Session = Depends(get_db),
):
    """
    Закрыть шкафчик перед выходом.
    """
    # Находим клиента по credential
    from app.services.credential_service import CredentialService
    cred_service = CredentialService(db)
    client = cred_service.find_client_by_credential(credential)
    
    if not client:
        raise HTTPException(404, "Клиент не найден")
    
    # Находим активную сессию шкафчика
    session = db.query(LockerSession).filter(
        LockerSession.client_id == client.id,
        LockerSession.status == "ACTIVE",
    ).first()
    
    if not session:
        raise HTTPException(404, "Нет активного шкафчика")
    
    # Закрываем шкафчик
    session.status = "CLOSED"
    session.ended_at = datetime.now()
    
    # Освобождаем шкафчик
    locker = db.query(Locker).filter(Locker.id == session.locker_id).first()
    if locker:
        locker.status = "FREE"
    
    db.commit()
    
    return {
        "success": True,
        "locker_number": locker.number if locker else None,
        "message": f"Шкафчик №{locker.number if locker else '?'} закрыт."
    }


@router.get("/status/{locker_id}")
def get_locker_status(locker_id: str, db: Session = Depends(get_db)):
    """Получить статус шкафчика"""
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(404, "Шкафчик не найден")
    return {"id": locker.id, "number": locker.number, "status": locker.status}


@router.get("/")
def list_lockers(db: Session = Depends(get_db)):
    """Список всех шкафчиков"""
    lockers = db.query(Locker).all()
    return [{"id": l.id, "number": l.number, "status": l.status} for l in lockers]