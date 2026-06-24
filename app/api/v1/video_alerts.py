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
    camera = db.query(Device).filter(Device.id == alert.camera_id, Device.device_type == "CAMERA").first()
    if not camera:
        raise HTTPException(status_code=404, detail="Камера не найдена")
    db_alert = VideoAlert(camera_id=alert.camera_id, alert_type=alert.alert_type.value, confidence=alert.confidence, snapshot_path=alert.snapshot_path, video_path=alert.video_path)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.get("", response_model=List[VideoAlertResponse])

async def list_alerts(camera_id: Optional[int] = None, alert_type: Optional[AlertType] = None, is_false_positive: Optional[bool] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, db: Session = Depends(get_db)):
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
    return query.order_by(VideoAlert.created_at.desc()).all()

@router.get("/{alert_id}", response_model=VideoAlertResponse)

async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(VideoAlert).filter(VideoAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Тревога не найдена")
    return alert

@router.post("/{alert_id}/review", response_model=VideoAlertResponse)

async def review_alert(alert_id: int, review: VideoAlertReviewRequest, db: Session = Depends(get_db)):
    alert = db.query(VideoAlert).filter(VideoAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Тревога не найдена")
    alert.is_false_positive = review.is_false_positive
    alert.reviewed_by = review.reviewed_by
    db.commit()
    db.refresh(alert)
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
