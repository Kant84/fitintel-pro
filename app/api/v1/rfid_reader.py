"""E16: RFID Reader API — с отслеживанием шкафчиков."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(prefix="/rfid", tags=["RFID Reader / Thin Client"])

class RFIDScanRequest(BaseModel):
    card_uid: str = Field(..., description="UID RFID-карты/браслета")
    device_id: Optional[str] = Field(None, description="ID считывателя ACR1252")

class RFIDScanResponse(BaseModel):
    found: bool
    client_id: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    subscription_name: Optional[str] = None
    subscription_expires: Optional[str] = None
    locker_number: Optional[str] = None
    locker_status: Optional[str] = None
    access_granted: bool = False
    message: str = ""

@router.post("/scan", response_model=RFIDScanResponse)
def rfid_scan(payload: RFIDScanRequest, db: Session = Depends(get_db)):
    # 1. Найти credential
    cred = db.execute(text("SELECT client_id FROM credentials WHERE credential_value = :uid AND credential_type = :rfid AND status = :active"),
        {"uid": payload.card_uid, "rfid": "RFID", "active": "active"}).fetchone()
    
    if not cred:
        return RFIDScanResponse(found=False, message="Карта не найдена в базе")
    
    client_id = str(cred[0])
    
    # 2. Найти клиента
    client = db.execute(text("SELECT first_name, last_name, phone FROM clients WHERE id = :cid"),
        {"cid": client_id}).fetchone()
    
    if not client:
        return RFIDScanResponse(found=False, message="Клиент не найден")
    
    full_name = f"{client[1]} {client[0]}"
    phone = client[2] or ""
    
    # 3. Найти активный абонемент
    sub = db.execute(text("""
        SELECT t.name, s.end_date FROM subscriptions s
        LEFT JOIN tariffs t ON s.tariff_id = t.id
        WHERE s.client_id = :cid AND s.status = :active AND s.end_date >= :today
        ORDER BY s.end_date DESC LIMIT 1
    """), {"cid": client_id, "active": "active", "today": date.today()}).fetchone()
    
    sub_name = sub[0] if sub else None
    sub_expires = str(sub[1]) if sub else None
    access = sub is not None
    
    # 4. Найти закрытый шкафчик клиента
    locker = db.execute(text("""
        SELECT locker_number, status FROM lockers
        WHERE client_id = :cid AND status = :occupied
        ORDER BY closed_at DESC LIMIT 1
    """), {"cid": client_id, "occupied": "occupied"}).fetchone()
    
    locker_num = locker[0] if locker else None
    locker_stat = locker[1] if locker else "none"
    
    return RFIDScanResponse(
        found=True,
        client_id=client_id,
        full_name=full_name,
        phone=phone,
        subscription_name=sub_name,
        subscription_expires=sub_expires,
        locker_number=locker_num,
        locker_status=locker_stat,
        access_granted=access,
        message="Доступ разрешен" if access else "Нет активного абонемента",
    )


# === Деактивация браслета после сброса ===
@router.post("/deactivate/{uid}")
def deactivate_credential(uid: str, db: Session = Depends(get_db)):
    """Деактивировать credential по UID (после сброса браслета)."""
    result = db.execute(text("""
        UPDATE credentials 
        SET status = 'inactive', updated_at = NOW() 
        WHERE credential_value = :uid AND credential_type = 'RFID'
        RETURNING id
    """), {"uid": uid})
    row = result.fetchone()
    db.commit()
    if row:
        return {"success": True, "message": "Браслет деактивирован"}
    return {"success": False, "message": "Браслет не найден в базе"}
