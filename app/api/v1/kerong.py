"""E16: Kerong Offline Locks — KR-S80 и другие модели."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.ml.event_logger import EventLogger

router = APIRouter(prefix="/kerong", tags=["Kerong Offline Locks"])

SUPPORTED_MODELS = ["KR-S50", "KR-S80", "KR-S100", "KR-S200", "KR-M16", "KR-M24", "KR-M40", "KR-PRO"]

class LockConfig(BaseModel):
    lock_id: str = Field(..., description="MAC или серийный номер")
    model: str = Field("KR-S80", description="Модель замка")
    lock_type: str = Field("cabinet", description="cabinet / door / gate")
    location: str = Field(..., description="Расположение")
    group: str = Field("mixed", description="man / women / mixed")

class CardAuthRequest(BaseModel):
    lock_id: str
    card_uid: str
    timestamp: Optional[str] = None

class CardAuthResponse(BaseModel):
    granted: bool
    lock_id: str
    card_uid: str
    expires_at: Optional[str] = None
    reason: Optional[str] = None

class SyncRequest(BaseModel):
    lock_id: str
    last_sync: Optional[str] = None

class SyncResponse(BaseModel):
    lock_id: str
    authorized_cards: List[str] = []
    revoked_cards: List[str] = []
    config: Dict = {}

@router.post("/auth", response_model=CardAuthResponse)
def auth_card(payload: CardAuthRequest, db: Session = Depends(get_db)):
    """Проверить карту при поднесении к KR-S80 (офлайн-режим)."""
    cred = db.execute(text("SELECT client_id FROM credentials WHERE credential_value = :uid AND credential_type = :rfid"),
        {"uid": payload.card_uid, "rfid": "RFID"}).fetchone()
    if not cred:
        return CardAuthResponse(granted=False, lock_id=payload.lock_id, card_uid=payload.card_uid, reason="Карта не найдена")
    
    sub = db.execute(text("SELECT end_date FROM subscriptions WHERE client_id = :cid AND status = :active AND end_date > NOW()"),
        {"cid": str(cred[0]), "active": "active"}).fetchone()
    
    if not sub:
        return CardAuthResponse(granted=False, lock_id=payload.lock_id, card_uid=payload.card_uid, reason="Нет активного абонемента")
    
    logger = EventLogger(db)
    logger.log_access(client_card=payload.card_uid, device_id=payload.lock_id, granted=True, client_id=str(cred[0]))
    
    return CardAuthResponse(granted=True, lock_id=payload.lock_id, card_uid=payload.card_uid, expires_at=str(sub[0]))

@router.post("/sync", response_model=SyncResponse)
def sync_lock(payload: SyncRequest, db: Session = Depends(get_db)):
    """Синхронизировать список карт с KR-S80 (раз в 5 мин)."""
    rows = db.execute(text("""
        SELECT c.credential_value FROM credentials c
        JOIN subscriptions s ON c.client_id = s.client_id
        WHERE c.credential_type = :rfid AND s.status = :active AND s.end_date > NOW()
    """), {"rfid": "RFID", "active": "active"}).fetchall()
    authorized = [r[0] for r in rows]
    return SyncResponse(lock_id=payload.lock_id, authorized_cards=authorized, revoked_cards=[],
        config={"sync_interval_sec": 300, "auto_lock_sec": 5, "model": "KR-S80"})

@router.get("/locks")
def list_locks():
    return {"supported_models": SUPPORTED_MODELS, "locks": []}

@router.post("/locks/register")
def register_lock(config: LockConfig):
    if config.model not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model {config.model} not supported")
    return {"status": "registered", "lock_id": config.lock_id, "model": config.model}
