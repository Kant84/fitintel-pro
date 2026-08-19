import base64
import io
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.client import Client
from app.models.face_id import FaceTemplate
from app.models.user import User
from app.schemas.face_id import FaceRegisterRequest, FaceVerifyRequest, FaceUpdateRequest, FaceTurnstileRequest
from app.services.face_id_service import FaceIDService

router = APIRouter(prefix="/face-id", tags=["Face ID"])

MIN_PHOTO_QUALITY = 40.0  # Вариация Лапласиана: < 40 = слишком размыто


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


@router.post("/register", status_code=201)
def register_face(data: FaceRegisterRequest, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if quality < MIN_PHOTO_QUALITY:
        raise HTTPException(status_code=400, detail="Низкое качество фото")
    service = FaceIDService(db)
    template = service.register_face(data.client_id, encoding, quality_score=quality)
    return {"face_template_id": template.id, "client_id": str(template.client_id),
            "embedding_size": len(encoding), "quality_score": round(quality, 1),
            "created_at": str(template.created_at)}


@router.post("/verify")
def verify_face(data: FaceVerifyRequest, db: Session = Depends(get_db)):
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        return {"matched": False, "confidence": 0.0, "reason": error}
    service = FaceIDService(db)
    template, confidence = service.find_best_match(encoding)
    if quality < MIN_PHOTO_QUALITY:
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


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    template = db.query(FaceTemplate).filter(FaceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    db.delete(template)
    db.commit()
    return None


@router.put("/{template_id}")
def update_template(template_id: int, data: FaceUpdateRequest, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    template = db.query(FaceTemplate).filter(FaceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if quality < MIN_PHOTO_QUALITY:
        raise HTTPException(status_code=400, detail="Низкое качество фото")
    template.face_encoding = encoding
    template.quality_score = quality
    db.commit()
    return {"id": template.id, "client_id": str(template.client_id), "updated": True,
            "quality_score": round(quality, 1)}


@router.post("/turnstile")
def face_turnstile(data: FaceTurnstileRequest, db: Session = Depends(get_db)):
    encoding, error, quality = extract_face_encoding(data.photo)
    if error:
        return {"access_granted": False, "turnstile_open": False, "reason": error}
    service = FaceIDService(db)
    if quality < MIN_PHOTO_QUALITY:
        service.log_recognition(None, data.device_id, "denied", "Низкое качество фото", 0.0)
        return {"access_granted": False, "turnstile_open": False, "reason": "Низкое качество фото"}
    template, confidence = service.find_best_match(encoding)
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
                                 device_id=data.device_id, zone=data.zone)
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
