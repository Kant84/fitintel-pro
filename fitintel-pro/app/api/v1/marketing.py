# app/api/v1/marketing.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db

router = APIRouter(prefix="/marketing", tags=["Marketing"])


@router.get("/campaigns")
def list_campaigns(
    current_user=Depends(require_permission("marketing.read")),
    db: Session = Depends(get_db),
):
    """Маркетинговые кампании"""
    return {"items": [], "count": 0}


@router.post("/campaigns")
def create_campaign(
    payload: dict,
    current_user=Depends(require_permission("marketing.create")),
    db: Session = Depends(get_db),
):
    """Создать кампанию"""
    import uuid
    from app.db.base import utc_now
    return {"id": str(uuid.uuid4()), "name": payload.get("name"), "status": "draft", "created_at": utc_now().isoformat()}


@router.get("/segments")
def client_segments(
    current_user=Depends(require_permission("marketing.read")),
    db: Session = Depends(get_db),
):
    """Сегменты клиентов"""
    return {"segments": [
        {"id": "new", "name": "Новые клиенты", "count": 0},
        {"id": "active", "name": "Активные", "count": 0},
        {"id": "sleeping", "name": "Спящие (30+ дней)", "count": 0},
        {"id": "churn", "name": "Отток", "count": 0},
    ]}


@router.post("/send-sms")
def send_sms(
    payload: dict,
    current_user=Depends(require_permission("marketing.send")),
    db: Session = Depends(get_db),
):
    """Отправить SMS-рассылку"""
    return {"status": "queued", "recipients": payload.get("client_ids", []), "message_preview": payload.get("text", "")[:50]}
