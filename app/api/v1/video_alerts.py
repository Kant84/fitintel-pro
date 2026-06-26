from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from app.api.dependencies import get_db, get_current_user
from app.models.video_alert import VideoAlert
from app.models.device import Device
from app.schemas.video_alert import VideoAlertCreate, VideoAlertResponse, VideoAlertReviewRequest
from app.schemas.enums import AlertType
from app.api.dependencies import require_permission

router = APIRouter(prefix="/video-alerts", tags=["Видеоаналитика (E12)"])

@router.post("", response_model=VideoAlertResponse, status_code=status.HTTP_201_CREATED)

async def create_alert(alert: VideoAlertCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    camera = db.query(Device).filter(Device.code == str(alert.camera_id), Device.device_type == "CAMERA").first()
    if not camera:
        raise HTTPException(status_code=404, detail="Камера не найдена")
    db_alert = VideoAlert(camera_id=alert.camera_id, alert_type=alert.alert_type.value, confidence=alert.confidence, snapshot=alert.snapshot)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    # Преобразуем UUID в str для ответа
    db_alert.id = str(db_alert.id)
    if db_alert.resolved_by:
        db_alert.resolved_by = str(db_alert.resolved_by)
    if db_alert.reviewed_by:
        db_alert.reviewed_by = str(db_alert.reviewed_by)
    return db_alert

@router.get("", response_model=List[VideoAlertResponse])

async def list_alerts(camera_id: Optional[str] = None, alert_type: Optional[AlertType] = None, is_false_positive: Optional[bool] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, db: Session = Depends(get_db)):
    query = db.query(VideoAlert)
    if camera_id:
        query = query.filter(VideoAlert.camera_id == camera_id)
    if alert_type:
        query = query.filter(VideoAlert.alert_type == alert_type.value)
    if is_false_positive is not None:
        query = query.filter(VideoAlert.is_false_positive == is_false_positive)
    if date_from:
        query = query.filter(VideoAlert.created_at >= date_from)
    if date_to:
        query = query.filter(VideoAlert.created_at <= date_to)
    alerts = query.order_by(VideoAlert.created_at.desc()).all()
    for alert in alerts:
        alert.id = str(alert.id)
        if alert.resolved_by:
            alert.resolved_by = str(alert.resolved_by)
        if alert.reviewed_by:
            alert.reviewed_by = str(alert.reviewed_by)
    return alerts

@router.get("/{alert_id}", response_model=VideoAlertResponse)

async def get_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(VideoAlert).filter(VideoAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Тревога не найдена")
    if alert.is_resolved:
        raise HTTPException(status_code=400, detail="Алерт уже разрешён")
    # Преобразуем UUID в str для ответа
    alert.id = str(alert.id)
    if alert.resolved_by:
        alert.resolved_by = str(alert.resolved_by)
    if alert.reviewed_by:
        alert.reviewed_by = str(alert.reviewed_by)
    return alert

@router.post("/{alert_id}/review", response_model=VideoAlertResponse)

async def review_alert(alert_id: str, review: VideoAlertReviewRequest, db: Session = Depends(get_db)):
    alert = db.query(VideoAlert).filter(VideoAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Тревога не найдена")
    if alert.is_resolved:
        raise HTTPException(status_code=400, detail="Алерт уже разрешён")
    alert.is_false_positive = review.is_false_positive
    alert.is_resolved = True
    alert.reviewed_by = review.reviewed_by
    db.commit()
    db.refresh(alert)
    # Преобразуем UUID в str для ответа
    alert.id = str(alert.id)
    if alert.resolved_by:
        alert.resolved_by = str(alert.resolved_by)
    if alert.reviewed_by:
        alert.reviewed_by = str(alert.reviewed_by)
    return alert

@router.get("/archive/cleanup")

async def cleanup_archive(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=30)
    old = db.query(VideoAlert).filter(VideoAlert.created_at < cutoff, VideoAlert.is_false_positive == True).all()
    count = len(old)
    for a in old:
        db.delete(a)
    db.commit()
    return {"deleted_count": count, "message": f"Удалено {count} старых тревог"}

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: str, db: Session = Depends(get_db)):
    """Удалить алерт"""
    alert = db.query(VideoAlert).filter(VideoAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")
    db.delete(alert)
    db.commit()
    return None

