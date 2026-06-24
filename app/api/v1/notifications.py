# app/api/v1/notifications.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.services.email_service import EmailService
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/email/send",
    status_code=status.HTTP_200_OK,
)
def send_email(
    to_email: str,
    subject: str,
    body: str,
    current_user=Depends(require_permission("notifications.send")),
    db: Session = Depends(get_db),
):
    """Отправить email (E17)"""
    result = EmailService.send_email(to_email, subject, body)
    return result


@router.post(
    "/email/digest",
    status_code=status.HTTP_200_OK,
)
def send_daily_digest(
    to_email: str,
    club_id: int = 1,
    current_user=Depends(require_permission("notifications.send")),
    db: Session = Depends(get_db),
):
    """Отправить ежедневный дайджест (E17)"""
    analytics = AnalyticsService(db)
    stats = analytics.dashboard(club_id)
    result = EmailService.send_daily_digest(to_email, stats)
    return result
