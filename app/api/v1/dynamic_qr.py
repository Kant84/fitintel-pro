import json
import base64
import hmac
import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, get_current_user
from app.models.client import Client
from app.models.dynamic_qr import DynamicQRCode
from app.models.subscription import Subscription
from app.schemas.dynamic_qr import DynamicQRCreate, DynamicQRResponse, QRValidateRequest, QRValidateResponse, GuestQRCreate, GroupQRCreate
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/dynamic-qr", tags=["Dynamic QR"])

QR_TTL = getattr(settings, 'QR_TTL_MINUTES', 5) * 60  # TTL из настроек клуба
QR_SECRET = getattr(settings, 'QR_SECRET_KEY', 'fitintel-qr-secret-2026')

def generate_qr_payload(client_id, expires, ttl, device_id=None):
    timestamp = int(time.time())
    client_id_str = str(client_id)
    payload = {"client_id": client_id_str, "timestamp": timestamp, "ttl": ttl, "expires_at": int(expires.timestamp())}
    payload["jti"] = uuid.uuid4().hex
    if device_id:
        payload["device_id"] = device_id
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(QR_SECRET.encode(), payload_json.encode(), hashlib.sha256).hexdigest()
    payload["signature"] = signature
    qr_payload = base64.b64encode(json.dumps(payload).encode()).decode()
    return qr_payload, signature, expires

def validate_qr(qr_payload: str, db: Session):
    try:
        data = json.loads(base64.b64decode(qr_payload))
        client_id = data.get("client_id")
        timestamp = data.get("timestamp")
        ttl = data.get("ttl")
        signature = data.get("signature")
        if not all([client_id, timestamp, ttl, signature]):
            return False, client_id, "Неверный формат QR"
        
        # Проверяем, не отозван ли QR
        qr_record = db.query(DynamicQRCode).filter(DynamicQRCode.qr_payload == qr_payload).first()
        if qr_record and qr_record.is_used:
            return False, client_id, "QR отозван или уже использован"
        
        # Проверяем время жизни
        if int(time.time()) > timestamp + ttl + 30:
            return False, client_id, "QR устарел"
        
        # Проверяем подпись
        payload = {"client_id": client_id, "timestamp": timestamp, "ttl": ttl, "expires_at": data.get("expires_at")}
        if data.get("jti"):
            payload["jti"] = data.get("jti")
        expected = hmac.new(QR_SECRET.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        if signature != expected:
            return False, client_id, "Неверная подпись"
        return True, client_id, "QR валиден"
    except Exception as e:
        return False, None, f"Ошибка проверки QR: {str(e)}"

@router.post("/generate", response_model=DynamicQRResponse)
async def generate_qr(qr_data: DynamicQRCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == qr_data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    # Проверяем активный абонемент
    active_sub = db.query(Subscription).filter(
        Subscription.client_id == qr_data.client_id,
        Subscription.status == "ACTIVE",
        Subscription.end_date > datetime.now(timezone.utc)
    ).first()
    if not active_sub:
        raise HTTPException(status_code=402, detail="Абонемент не активен")
    expires = datetime.now(timezone.utc) + timedelta(minutes=qr_data.expires_in_minutes)
    payload, signature, _ = generate_qr_payload(qr_data.client_id, expires, qr_data.expires_in_minutes * 60, getattr(qr_data, 'device_id', None))
    db_qr = DynamicQRCode(client_id=qr_data.client_id, qr_payload=payload, signature=signature, expires_at=expires, is_used=False)
    db.add(db_qr)
    db.commit()
    db.refresh(db_qr)
    return db_qr

@router.post("/validate", response_model=QRValidateResponse)
async def validate_qr_endpoint(data: QRValidateRequest, db: Session = Depends(get_db)):
    is_valid, client_id, message = validate_qr(data.qr_payload, db)
    if not is_valid:
        return QRValidateResponse(valid=False, client_id=client_id, message=message, access_granted=False)
    subscription = db.query(Subscription).filter(Subscription.client_id == client_id, Subscription.status == "ACTIVE", Subscription.end_date > datetime.now(timezone.utc)).first()
    if not subscription:
        return QRValidateResponse(valid=True, client_id=client_id, message="Нет активного абонемента", access_granted=False)
    qr_record = db.query(DynamicQRCode).filter(DynamicQRCode.qr_payload == data.qr_payload).first()
    if qr_record:
        qr_record.is_used = True
        db.commit()
    return QRValidateResponse(valid=True, client_id=client_id, message="Доступ разрешён", access_granted=True)

@router.get("/my", response_model=DynamicQRResponse)
async def get_my_qr(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(DynamicQRCode).filter(DynamicQRCode.client_id == current_user.id, DynamicQRCode.expires_at > datetime.now(timezone.utc), DynamicQRCode.is_used == False).order_by(DynamicQRCode.created_at.desc()).first()
    if existing:
        return existing
    payload, signature, expires = generate_qr_payload(current_user.id, datetime.now(timezone.utc) + timedelta(seconds=QR_TTL), QR_TTL)
    db_qr = DynamicQRCode(client_id=current_user.id, qr_payload=payload, signature=signature, expires_at=expires, is_used=False)
    db.add(db_qr)
    db.commit()
    db.refresh(db_qr)
    return db_qr

@router.post("/{qr_id}/revoke", response_model=dict)
async def revoke_qr(qr_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    qr = db.query(DynamicQRCode).filter(DynamicQRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR не найден")
    if qr.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    if qr.is_used:
        raise HTTPException(status_code=400, detail="QR уже использован")
    qr.is_used = True
    db.commit()
    return {"success": True, "message": "QR отозван", "qr_id": str(qr_id)}


@router.post("/verify")
async def verify_qr_endpoint(data: QRValidateRequest, db: Session = Depends(get_db)):
    try:
        raw = json.loads(base64.b64decode(data.qr_payload))
    except Exception:
        raise HTTPException(status_code=403, detail="Подпись недействительна")
    client_id = raw.get("client_id")
    timestamp = raw.get("timestamp")
    ttl = raw.get("ttl")
    signature = raw.get("signature")
    if not all([client_id, timestamp, ttl, signature]):
        raise HTTPException(status_code=403, detail="Подпись недействительна")
    payload = {"client_id": client_id, "timestamp": timestamp, "ttl": ttl, "expires_at": raw.get("expires_at")}
    if raw.get("device_id"):
        payload["device_id"] = raw["device_id"]
    if raw.get("jti"):
        payload["jti"] = raw["jti"]
    expected = hmac.new(QR_SECRET.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    if signature != expected:
        raise HTTPException(status_code=403, detail="Подпись недействительна")
    bound_device = raw.get("device_id")
    if bound_device and data.device_id != bound_device:
        raise HTTPException(status_code=403, detail="QR привязан к другому устройству")
    qr_record = db.query(DynamicQRCode).filter(DynamicQRCode.qr_payload == data.qr_payload).first()
    if qr_record and qr_record.is_used:
        raise HTTPException(status_code=410, detail="QR уже использован")
    if int(time.time()) > timestamp + ttl + 30:
        raise HTTPException(status_code=410, detail="QR истёк")
    if qr_record:
        qr_record.uses_count = (qr_record.uses_count or 0) + 1
        if qr_record.uses_count >= (qr_record.max_uses or 1):
            qr_record.is_used = True
        db.commit()
    return {"valid": True, "client_id": client_id, "signature_valid": True}

@router.get("")
async def get_client_qr(client_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    qr = db.query(DynamicQRCode).filter(
        DynamicQRCode.client_id == client_id,
        DynamicQRCode.expires_at > datetime.now(timezone.utc),
        DynamicQRCode.is_used == False
    ).order_by(DynamicQRCode.created_at.desc()).first()
    if not qr:
        return None
    return qr


@router.post("/guest", status_code=201)
async def create_guest_qr(data: GuestQRCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expires = datetime.now(timezone.utc) + timedelta(minutes=data.expires_in_minutes)
    payload, signature, _ = generate_qr_payload(f"guest:{data.email}", expires, data.expires_in_minutes * 60)
    db_qr = DynamicQRCode(client_id=None, qr_payload=payload, signature=signature, expires_at=expires,
                          is_used=False, qr_type="GUEST", max_uses=1, guest_email=data.email)
    db.add(db_qr)
    db.commit()
    db.refresh(db_qr)
    return {"id": str(db_qr.id), "qr_payload": payload, "expires_at": expires.isoformat(),
            "qr_type": "GUEST", "guest_email": data.email, "max_uses": 1}

@router.post("/group", status_code=201)
async def create_group_qr(data: GroupQRCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not data.client_ids:
        raise HTTPException(status_code=422, detail="Список клиентов пуст")
    expires = datetime.now(timezone.utc) + timedelta(minutes=data.expires_in_minutes)
    group_id = str(uuid.uuid4())
    payload, signature, _ = generate_qr_payload(f"group:{group_id}", expires, data.expires_in_minutes * 60)
    db_qr = DynamicQRCode(client_id=None, qr_payload=payload, signature=signature, expires_at=expires,
                          is_used=False, qr_type="GROUP", max_uses=len(data.client_ids),
                          client_ids=json.dumps([str(c) for c in data.client_ids]))
    db.add(db_qr)
    db.commit()
    db.refresh(db_qr)
    return {"id": str(db_qr.id), "qr_payload": payload, "expires_at": expires.isoformat(),
            "qr_type": "GROUP", "max_uses": len(data.client_ids), "client_ids": [str(c) for c in data.client_ids]}


@router.post("/turnstile")
async def turnstile_qr_scan(
    qr_payload: str = Body(...),
    device_id: str = Body(...),
    zone: str = Body(None),
    db: Session = Depends(get_db),
):
    """Сканер на турникете: проверяет QR и открывает турникет (E20.14)."""
    from fastapi import Body
    # 1. Декодируем и проверяем подпись
    try:
        raw = json.loads(base64.b64decode(qr_payload))
    except Exception:
        raise HTTPException(status_code=403, detail="Подпись недействительна")
    client_id = raw.get("client_id")
    timestamp = raw.get("timestamp")
    ttl = raw.get("ttl")
    signature = raw.get("signature")
    if not all([client_id, timestamp, ttl, signature]):
        raise HTTPException(status_code=403, detail="Подпись недействительна")
    payload = {"client_id": client_id, "timestamp": timestamp, "ttl": ttl, "expires_at": raw.get("expires_at")}
    if raw.get("device_id"):
        payload["device_id"] = raw["device_id"]
    if raw.get("jti"):
        payload["jti"] = raw["jti"]
    expected = hmac.new(QR_SECRET.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    if signature != expected:
        raise HTTPException(status_code=403, detail="Подпись недействительна")
    qr_record = db.query(DynamicQRCode).filter(DynamicQRCode.qr_payload == qr_payload).first()
    if qr_record and qr_record.is_used:
        raise HTTPException(status_code=410, detail="QR уже использован")
    if int(time.time()) > timestamp + ttl + 30:
        raise HTTPException(status_code=410, detail="QR истёк")
    if qr_record:
        qr_record.uses_count = (qr_record.uses_count or 0) + 1
        if qr_record.uses_count >= (qr_record.max_uses or 1):
            qr_record.is_used = True
        db.commit()

    # 2. Открываем турникет через AccessService
    from app.services.access_service import AccessService
    client = db.query(Client).filter(Client.id == client_id).first() if not str(client_id).startswith(("guest:", "group:")) else None
    credential = (client.phone or client.email) if client else str(client_id)
    service = AccessService(db)
    result = service.grant_access(credential=credential, device_id=device_id, zone=zone)
    return {
        "access_granted": result.granted,
        "turnstile_open": result.granted,
        "client_id": client_id,
        "reason": result.reason,
        "visit_id": str(result.visit_id) if result.visit_id else None,
        "device_id": device_id,
    }
