from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import VideoAlert, Device
from app.schemas import (
    VideoAlertCreate, VideoAlertResponse, VideoAlertReviewRequest,
    ErrorResponse
)
from app.schemas.enums import AlertType, DeviceStatus
from app.core.auth import get_current_user, require_permission
from app.core.audit import log_action

router = APIRouter(prefix="/video-alerts", tags=["Видеоаналитика / Тревоги (E12)"])


@router.post("", response_model=VideoAlertResponse, status_code=status.HTTP_201_CREATED)
@require_permission("video_alerts.create")
async def create_alert(
    alert: VideoAlertCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E12.9-E12.14 — Создание тревожного события
    Типы: fall, fight, smoke, left_object, crowd, wrong_direction, custom
    """
    # Проверяем камеру
    camera = db.query(Device).filter(
        Device.id == alert.camera_id,
        Device.device_type == "camera"
    ).first()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Камера #{alert.camera_id} не найдена",
                "code": "CAMERA_NOT_FOUND",
                "suggestion": "Проверьте ID камеры или добавьте через Device Manager"
            }
        )

    db_alert = VideoAlert(
        camera_id=alert.camera_id,
        alert_type=alert.alert_type.value,
        confidence=alert.confidence,
        snapshot_path=alert.snapshot_path,
        video_path=alert.video_path,
        is_false_positive=False,
        reviewed_by=None
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    # Отправка уведомлений (E12.9, E18.8)
    # В реальности: WebSocket, Telegram, MAX Bot, Desktop notification

    log_action(
        db=db,
        user_id=current_user.id,
        action="video_alert_created",
        entity_type="video_alert",
        entity_id=db_alert.id,
        details={
            "camera_id": alert.camera_id,
            "alert_type": alert.alert_type.value,
            "confidence": alert.confidence
        }
    )

    return db_alert


@router.get("", response_model=List[VideoAlertResponse])
@require_permission("video_alerts.read")
async def list_alerts(
    camera_id: Optional[int] = None,
    alert_type: Optional[AlertType] = None,
    is_false_positive: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E12.18-E12.19 — Список тревожных событий с фильтрами
    """
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
    return alerts


@router.get("/{alert_id}", response_model=VideoAlertResponse)
@require_permission("video_alerts.read")
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E12 — Получить тревогу по ID
    """
    alert = db.query(VideoAlert).filter(VideoAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Тревога #{alert_id} не найдена",
                "code": "ALERT_NOT_FOUND",
                "suggestion": "Проверьте ID тревоги"
            }
        )
    return alert


@router.post("/{alert_id}/review", response_model=VideoAlertResponse)
@require_permission("video_alerts.review")
async def review_alert(
    alert_id: int,
    review: VideoAlertReviewRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E12.17 — Пометка тревоги как ложной (обучение модели)
    """
    alert = db.query(VideoAlert).filter(VideoAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Тревога #{alert_id} не найдена",
                "code": "ALERT_NOT_FOUND",
                "suggestion": "Проверьте ID тревоги"
            }
        )

    alert.is_false_positive = review.is_false_positive
    alert.reviewed_by = review.reviewed_by

    db.commit()
    db.refresh(alert)

    # В реальности: отправка обратной связи в модель для дообучения

    log_action(
        db=db,
        user_id=current_user.id,
        action="alert_reviewed",
        entity_type="video_alert",
        entity_id=alert_id,
        details={
            "is_false_positive": review.is_false_positive,
            "reviewed_by": review.reviewed_by
        }
    )

    return alert


@router.get("/archive/cleanup")
@require_permission("video_alerts.manage")
async def cleanup_archive(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E12.18-E12.19 — Очистка архива тревог
    Удаление файлов старше 30 дней
    """
    cutoff_date = datetime.utcnow() - timedelta(days=30)

    old_alerts = db.query(VideoAlert).filter(
        VideoAlert.created_at < cutoff_date,
        VideoAlert.is_false_positive == True  # Только подтверждённые ложные
    ).all()

    deleted_count = 0
    for alert in old_alerts:
        # В реальности: удаление файлов с диска/S3
        db.delete(alert)
        deleted_count += 1

    db.commit()

    return {
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat(),
        "message": f"Удалено {deleted_count} старых тревог"
    }


@router.get("/stats/daily")
@require_permission("video_alerts.read")
async def get_daily_stats(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    E12 — Статистика тревог по дням
    """
    from sqlalchemy import func

    query_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.utcnow().date()

    stats = db.query(
        VideoAlert.alert_type,
        func.count(VideoAlert.id).label("count")
    ).filter(
        func.date(VideoAlert.created_at) == query_date
    ).group_by(VideoAlert.alert_type).all()

    return {
        "date": query_date.isoformat(),
        "total_alerts": sum(s.count for s in stats),
        "by_type": [{"type": s.alert_type, "count": s.count} for s in stats]
    }
