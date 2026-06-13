# app/api/v1/marketing.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.services.marketing_service import MarketingService

router = APIRouter(prefix="/marketing", tags=["Marketing"])


def get_service(db: Session = Depends(get_db)) -> MarketingService:
    return MarketingService(db)


# ============================================================
# СЕГМЕНТЫ
# ============================================================

@router.get("/segments")
def client_segments(
    current_user=Depends(require_permission("marketing.read")),
    service: MarketingService = Depends(get_service),
):
    """Сегменты клиентов с реальной аналитикой"""
    return {"segments": service.get_segments()}


@router.get("/segments/{segment_id}/clients")
def segment_clients(
    segment_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_permission("marketing.read")),
    service: MarketingService = Depends(get_service),
):
    """Клиенты конкретного сегмента"""
    return service.get_segment_clients(segment_id, offset, limit)


# ============================================================
# SMS РАССЫЛКА
# ============================================================

@router.post("/send-sms")
def send_sms(
    payload: dict,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Отправить SMS на конкретные номера"""
    return service.send_sms(
        phones=payload.get("phones", []),
        message=payload.get("text", ""),
        campaign_name=payload.get("campaign_name"),
        actor_user_id=current_user.id,
    )


@router.post("/segments/{segment_id}/send-sms")
def send_sms_to_segment(
    segment_id: str,
    payload: dict,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Отправить SMS сегменту клиентов"""
    return service.send_sms_to_segment(
        segment_id=segment_id,
        message=payload.get("text", ""),
        campaign_name=payload.get("campaign_name"),
        actor_user_id=current_user.id,
    )


# ============================================================
# EMAIL РАССЫЛКА
# ============================================================

@router.post("/send-email")
def send_email(
    payload: dict,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Отправить email-рассылку"""
    return service.send_email(
        to_emails=payload.get("emails", []),
        subject=payload.get("subject", ""),
        body=payload.get("body", ""),
        html=payload.get("html", False),
        campaign_name=payload.get("campaign_name"),
        actor_user_id=current_user.id,
    )


# ============================================================
# КАМПАНИИ
# ============================================================

@router.get("/campaigns")
def list_campaigns(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user=Depends(require_permission("marketing.read")),
    service: MarketingService = Depends(get_service),
):
    """Маркетинговые кампании"""
    return service.list_campaigns(offset, limit)


@router.post("/campaigns")
def create_campaign(
    payload: dict,
    current_user=Depends(require_permission("marketing.create")),
    service: MarketingService = Depends(get_service),
):
    """Создать кампанию"""
    return service.create_campaign(payload, actor_user_id=current_user.id)


@router.post("/campaigns/{campaign_id}/launch")
def launch_campaign(
    campaign_id: UUID,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Запустить кампанию"""
    return service.launch_campaign(campaign_id, actor_user_id=current_user.id)
