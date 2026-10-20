import base64
import io
import os
import threading
import time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as _sql_text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.dependencies import get_db, get_current_user
from app.models.client import Client
from app.models.face_id import FaceTemplate
from app.models.user import User
from app.schemas.face_id import FaceRegisterRequest, FaceVerifyRequest, FaceUpdateRequest, FaceTurnstileRequest
from app.services.face_id_service import FaceIDService
from app.schemas.enums import AccessMethod 

def _warmup_face_models():
    """Прогрев dlib/ResNet в фоне при старте — иначе первый запрос грузит модель 10-60 сек."""
    try:
        import numpy as np
        import face_recognition
        img = np.zeros((96, 96, 3), dtype=np.uint8)
        face_recognition.face_encodings(img)   # загружает ResNet в память процесса
    except Exception:
        pass


threading.Thread(target=_warmup_face_models, daemon=True).start()

router = APIRouter(prefix="/face-id", tags=["Face ID"])


# ---------------------------------------------------------------------------
# Настройки движка — ПОД КЛУБ (хранятся в БД, правятся с экрана «Face ID»)
# ---------------------------------------------------------------------------

def _face_settings(db) -> dict:
    try:
        row = db.execute(_sql_text(
            "SELECT threshold, min_quality, max_templates, store_photos "
            "FROM face_settings WHERE id=1")).first()
        if row:
            return {"threshold": float(row[0]), "min_quality": float(row[1]),
                    "max_templates": int(row[2]), "store_photos": bool(row[3])}
    except Exception:
        pass
    return {"threshold": 0.6, "min_quality": 40.0, "max_templates": 5,
            "store_photos": False}


class FaceSettingsIn(BaseModel):
    threshold: float = 0.6
    min_quality: float = 40.0
    max_templates: int = 5
    store_photos: bool = False


@router.get("/settings")
def get_face_settings(db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    return _face_settings(db)


@router.put("/settings")
def set_face_settings(data: FaceSettingsIn, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    db.execute(_sql_text(
        "INSERT INTO face_settings (id, threshold, min_quality, max_templates, store_photos) "
        "VALUES (1, :t, :q, :m, :s) ON CONFLICT (id) DO UPDATE SET "
        "threshold=EXCLUDED.threshold, min_quality=EXCLUDED.min_quality, "
        "max_templates=EXCLUDED.max_templates, store_photos=EXCLUDED.store_photos"),
        {"t": max(0.1, min(1.5, data.threshold)),
         "q": max(1.0, data.min_quality),
         "m": max(1, min(20, data.max_templates)),
         "s": bool(data.store_photos)})
    db.commit()
    return _face_settings(db)


# ---------------------------------------------------------------------------
# Хранилище фото (опционально — включает клуб; по умолчанию выкл, 152-ФЗ)
# ---------------------------------------------------------------------------
FACE_PHOTOS_DIR = "/app/data/face_photos"


def _store_photo(photo_b64: str, template_id, client_id) -> str | None:
    """Сохранить фото лица на диск (только если клуб включил хранение).
    Возвращает имя файла или None. Права 600 — только владелец."""
    try:
        os.makedirs(FACE_PHOTOS_DIR, exist_ok=True)
        fname = f"tpl{template_id}_c{str(client_id)[:8]}_{int(time.time())}.jpg"
        path = os.path.join(FACE_PHOTOS_DIR, fname)
        with open(path, "wb") as f:
            f.write(base64.b64decode(photo_b64))
        os.chmod(path, 0o600)
        return fname
    except Exception:
        return None


def _remove_photo(fname: str | None):
    if not fname:
        return
    try:
        os.remove(os.path.join(FACE_PHOTOS_DIR, fname))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Ядро
# ---------------------------------------------------------------------------

def extract_face_encoding(photo_b64: str):
    """Извлечь эмбеддинг + оценка резкости. Возвращает (encoding, error, quality)."""
    import face_recognition
    import numpy as np
    try:
        image_data = base64.b64decode(photo_b64)
        img = face_recognition.load_image_file(io.BytesIO(image_data))
    except Exception:
        return None, "Невалидное изображение", 0.0
    gray = img.astype(np.float64).mean(axis=2)
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    quality = float(lap.var())
    encodings = face_recognition.face_encodings(img)
    if len(encodings) == 0:
        return None, "Лицо не обнаружено", quality
    if len(encodings) > 1:
        return None, "Обнаружено несколько лиц", quality
    return encodings[0].tolist(), None, quality


def _require_biometric_consent(db, client_id):
    """Этап В (152-ФЗ): шаблон Face ID — только при активном согласии на обработку биометрии."""
    try:
        db.execute(_sql_text(
            "CREATE TABLE IF NOT EXISTS client_consents ("
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "client_id TEXT NOT NULL, consent_type VARCHAR(64) NOT NULL,"
            "status VARCHAR(16) NOT NULL DEFAULT 'granted',"
            "granted_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ, granted_by TEXT,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "UNIQUE(client_id, consent_type))"))
        db.commit()
    except Exception:
        db.rollback()
    row = db.execute(_sql_text(
        "SELECT 1 FROM client_consents WHERE client_id = :c "
        "AND consent_type = 'biometric_processing' AND status = 'granted'"),
        {"c": str(client_id)}).first()
    if not row:
        raise HTTPException(status_code=403, detail="biometric_consent_required")

@router.post("/register", status_code=201)
def register_face(data: FaceRegisterRequest, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    _require_biometric_consent(db, data.client_id)
    settings = _face_settings(db)
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if quality < settings["min_quality"]:
        raise HTTPException(status_code=400, detail="Низкое качество фото")
    existing = db.query(FaceTemplate).filter(
        FaceTemplate.client_id == data.client_id,
        FaceTemplate.is_active == True).count()
    if existing >= settings["max_templates"]:
        raise HTTPException(status_code=400,
                            detail=f"Лимит шаблонов ({settings['max_templates']}) для клиента исчерпан")
    service = FaceIDService(db)
    template = service.register_face(data.client_id, encoding, quality_score=quality)
    photo_stored = False
    if settings.get("store_photos"):
        fname = _store_photo(data.photo, template.id, data.client_id)
        if fname:
            template.photo_path = fname
            db.commit()
            photo_stored = True
    from app.services.audit_service import AuditService
    AuditService(db).created(
        actor_user_id=current_user.id, entity_type="face_template", entity_id=None,
        message=(f"Зарегистрирован шаблон Face ID: {client.last_name} {client.first_name} "
                 f"(качество {round(quality, 1)}{', фото сохранено' if photo_stored else ''})"))
    return {"face_template_id": template.id, "client_id": str(template.client_id),
            "embedding_size": len(encoding), "quality_score": round(quality, 1),
            "photo_stored": photo_stored,
            "created_at": str(template.created_at)}


@router.post("/verify")
def verify_face(data: FaceVerifyRequest, db: Session = Depends(get_db)):
    settings = _face_settings(db)
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        return {"matched": False, "confidence": 0.0, "reason": error}
    service = FaceIDService(db)
    template, confidence = service.find_best_match(encoding, threshold=settings["threshold"])
    if quality < settings["min_quality"]:
        return {"matched": False, "confidence": round(confidence, 4),
                "reason": "Низкое качество фото"}
    if not template:
        reason = "Низкая уверенность" if confidence >= 0.4 else "Совпадений не найдено"
        return {"matched": False, "confidence": round(confidence, 4), "reason": reason}
    return {"matched": True, "client_id": str(template.client_id),
            "confidence": round(confidence, 4), "face_template_id": template.id}


@router.get("")
def list_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    templates = db.query(FaceTemplate).filter(FaceTemplate.is_active == True).all()
    return [{"id": t.id, "client_id": str(t.client_id), "is_primary": t.is_primary,
             "quality_score": t.quality_score, "created_at": str(t.created_at)} for t in templates]


@router.get("/templates")
def list_templates_alias(db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """Алиас для тонкого клиента: GET /face-id/templates == GET /face-id/"""
    return list_templates(db, current_user)


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    template = db.query(FaceTemplate).filter(FaceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    _remove_photo(getattr(template, "photo_path", None))
    from app.services.audit_service import AuditService
    AuditService(db).deleted(
        actor_user_id=current_user.id, entity_type="face_template",
        entity_id=template.id,
        message=f"Удалён шаблон Face ID клиента {template.client_id}")
    db.delete(template)
    db.commit()
    return None


@router.put("/{template_id}")
def update_template(template_id: int, data: FaceUpdateRequest, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    template = db.query(FaceTemplate).filter(FaceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    _require_biometric_consent(db, template.client_id)
    settings = _face_settings(db)
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if quality < settings["min_quality"]:
        raise HTTPException(status_code=400, detail="Низкое качество фото")
    template.face_encoding = encoding
    template.quality_score = quality
    db.commit()
    if settings.get("store_photos"):
        fname = _store_photo(data.photo, template.id, template.client_id)
        if fname:
            _remove_photo(getattr(template, "photo_path", None))
            template.photo_path = fname
            db.commit()
    return {"id": template.id, "client_id": str(template.client_id), "updated": True,
            "quality_score": round(quality, 1)}


@router.post("/turnstile")
def face_turnstile(data: FaceTurnstileRequest, db: Session = Depends(get_db)):
    settings = _face_settings(db)
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        return {"access_granted": False, "turnstile_open": False, "reason": error}
    service = FaceIDService(db)
    if quality < settings["min_quality"]:
        service.log_recognition(None, data.device_id, "denied", "Низкое качество фото", 0.0)
        return {"access_granted": False, "turnstile_open": False, "reason": "Низкое качество фото"}
    template, confidence = service.find_best_match(encoding, threshold=settings["threshold"])
    if not template:
        service.log_recognition(None, data.device_id, "denied", "Лицо не распознано", confidence)
        return {"access_granted": False, "turnstile_open": False,
                "reason": "Лицо не распознано", "confidence": round(confidence, 4)}
    if not service.has_active_subscription(template.client_id):
        service.log_recognition(template.id, data.device_id, "denied", "Абонемент не активен", confidence)
        return {"access_granted": False, "turnstile_open": False,
                "reason": "Абонемент не активен", "client_id": str(template.client_id)}
    client = db.query(Client).filter(Client.id == template.client_id).first()
    from app.services.access_service import AccessService
    access = AccessService(db)
    result = access.grant_access(credential=client.phone or client.email,
                                 device_id=data.device_id, zone=data.zone,
                                 access_method=AccessMethod.FACE_ID)
    service.log_recognition(template.id, data.device_id,
                            "granted" if result.granted else "denied", result.reason, confidence)
    return {"access_granted": result.granted, "turnstile_open": result.granted,
            "client_id": str(template.client_id), "confidence": round(confidence, 4),
            "visit_id": str(result.visit_id) if result.visit_id else None,
            "device_id": data.device_id}

@router.get("/engine/info")
def face_engine_info():
    """E27.14: Информация о движке распознавания лиц."""
    import face_recognition
    return {"engine": "dlib", "library": "face_recognition",
            "library_version": face_recognition.__version__,
            "model": "ResNet-34 (dlib)", "embedding_size": 128}


def _screen_score(img):
    """Детекция 'фото с экрана': энергия узких линий пиксельной решётки в FFT."""
    import numpy as np
    g = img.astype(np.float64).mean(axis=2)
    g = g - g.mean()
    F = np.abs(np.fft.fftshift(np.fft.fft2(g))) ** 2
    h, w = g.shape
    fy = np.abs(np.fft.fftshift(np.fft.fftfreq(h)))[:, None]
    fx = np.abs(np.fft.fftshift(np.fft.fftfreq(w)))[None, :]
    hf = (fx > 0.15) | (fy > 0.15)
    lines = ((fx > 0.3) & (fy < 0.03)) | ((fy > 0.3) & (fx < 0.03))
    return float(F[lines].sum() / (F[hf].sum() + 1e-9))


def _eye_aspect_ratio(eye):
    import math
    return (math.dist(eye[1], eye[5]) + math.dist(eye[2], eye[4])) / (2.0 * math.dist(eye[0], eye[3]) + 1e-9)


@router.post("/anti-spoofing")
def anti_spoofing(data: FaceVerifyRequest, db: Session = Depends(get_db)):
    """E27.12: Проверка, что фото живое, а не снимок экрана/распечатка."""
    import face_recognition
    try:
        img = face_recognition.load_image_file(io.BytesIO(base64.b64decode(data.photo)))
    except Exception:
        raise HTTPException(status_code=400, detail="Невалидное изображение")
    score = _screen_score(img)
    if score > 0.5:
        raise HTTPException(status_code=403, detail="Обнаружена попытка обмана")
    return {"is_real": True, "screen_score": round(score, 4)}


@router.post("/liveness")
def liveness_check(data: dict, db: Session = Depends(get_db)):
    """E27.13: Liveness по серии кадров — детекция моргания (EAR)."""
    import face_recognition
    frames = data.get("frames", [])
    if len(frames) < 2:
        raise HTTPException(status_code=422, detail="Нужно минимум 2 кадра")
    ears = []
    for frame_b64 in frames:
        try:
            img = face_recognition.load_image_file(io.BytesIO(base64.b64decode(frame_b64)))
        except Exception:
            return {"liveness": False, "reason": "Невалидный кадр"}
        landmarks = face_recognition.face_landmarks(img)
        if not landmarks:
            return {"liveness": False, "reason": "Лицо не найдено в кадре"}
        face = landmarks[0]
        ear = (_eye_aspect_ratio(face["left_eye"]) + _eye_aspect_ratio(face["right_eye"])) / 2
        ears.append(ear)
    blinked = (max(ears) - min(ears)) > 0.08 and min(ears) < 0.22
    return {"liveness": blinked, "ear_values": [round(e, 3) for e in ears]}