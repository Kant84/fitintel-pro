from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hmac, hashlib, base64, json

from app.api.dependencies import get_db, get_current_user
from app.models.dynamic_qr import DynamicQRCode
from app.models.client import Client
from app.models.subscription import Subscription
from app.schemas.dynamic_qr import DynamicQRCreate, DynamicQRResponse, QRValidateRequest, QRValidateResponse
from app.core.config import settings

router = APIRouter(prefix="/qr", tags=["Динамический QR (E20)"])

QR_TTL = 300  # 5 minutes
QR_SECRET = getattr(settings, 'QR_SECRET_KEY', 'fitintel-qr-secret-2026')

def generate_qr_payload(client_id: int):
    timestamp = int(datetime.utcnow().timestamp())
    expires = datetime.utcnow() + timedelta(seconds=QR_TTL)
    payload = {"client_id": client_id, "timestamp": timestamp, "ttl": QR_TTL, "expires_at": int(expires.timestamp())}
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(QR_SECRET.encode(), payload_json.encode(), hashlib.sha256).hexdigest()
    payload["signature"] = signature
    qr_payload = base64.b64encode(json.dumps(payload).encode()).decode()
    return qr_payload, signature, expires

def validate_qr(qr_payload: str):
    try:
        data = json.loads(base64.b64decode(qr_payload))
        client_id = data.get("client_id")
        timestamp = data.get("timestamp")
        ttl = data.get("ttl")
        signature = data.get("signature")
        if not all([client_id, timestamp, ttl, signature]):
            return False, client_id, "Неверный формат QR"
        if int(datetime.utcnow().timestamp()) > timestamp + ttl + 30:
            return False, client_id, "QR устарел"
        payload = {"client_id": client_id, "timestamp": timestamp, "ttl": ttl, "expires_at": data.get("expires_at")}
        expected = hmac.new(QR_SECRET.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False, client_id, "Подпись невалидна"
        return True, client_id, "QR валиден"
    except Exception as e:
        return False, None, f"Ошибка: {str(e)}"

@router.post("/generate", response_model=DynamicQRResponse)
async def generate_qr(qr_data: DynamicQRCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == qr_data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    payload, signature, expires = generate_qr_payload(qr_data.client_id)
    db_qr = DynamicQRCode(client_id=qr_data.client_id, qr_payload=payload, signature=signature, expires_at=expires, is_used=False)
    db.add(db_qr)
    db.commit()
    db.refresh(db_qr)
    return db_qr

@router.post("/validate", response_model=QRValidateResponse)
async def validate_qr_endpoint(data: QRValidateRequest, db: Session = Depends(get_db)):
    is_valid, client_id, message = validate_qr(data.qr_payload)
    if not is_valid:
        return QRValidateResponse(valid=False, client_id=client_id, message=message, access_granted=False)
    subscription = db.query(Subscription).filter(Subscription.client_id == client_id, Subscription.status == "ACTIVE", Subscription.end_date > datetime.utcnow()).first()
    if not subscription:
        return QRValidateResponse(valid=True, client_id=client_id, message="Нет активного абонемента", access_granted=False)
    existing = db.query(DynamicQRCode).filter(DynamicQRCode.qr_payload == data.qr_payload, DynamicQRCode.is_used == True).first()
    if existing:
        return QRValidateResponse(valid=False, client_id=client_id, message="QR уже использован", access_granted=False)
    qr_record = db.query(DynamicQRCode).filter(DynamicQRCode.qr_payload == data.qr_payload).first()
    if qr_record:
        qr_record.is_used = True
        db.commit()
    return QRValidateResponse(valid=True, client_id=client_id, message="Доступ разрешён", access_granted=True)

@router.get("/my", response_model=DynamicQRResponse)
async def get_my_qr(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    existing = db.query(DynamicQRCode).filter(DynamicQRCode.client_id == current_user.id, DynamicQRCode.expires_at > datetime.utcnow(), DynamicQRCode.is_used == False).order_by(DynamicQRCode.created_at.desc()).first()
    if existing:
        return existing
    payload, signature, expires = generate_qr_payload(current_user.id)
    db_qr = DynamicQRCode(client_id=current_user.id, qr_payload=payload, signature=signature, expires_at=expires, is_used=False)
    db.add(db_qr)
    db.commit()
    db.refresh(db_qr)
    return db_qr
