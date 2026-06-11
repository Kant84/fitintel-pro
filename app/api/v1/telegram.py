# app/api/v1/telegram.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.services.telegram_bot_service import TelegramBotService
from app.api.dependencies import require_permission

router = APIRouter(prefix="/telegram", tags=["Telegram Bot"])


class WebhookPayload(BaseModel):
    update_id: int
    message: dict | None = None
    callback_query: dict | None = None


class SendMessageRequest(BaseModel):
    chat_id: str
    text: str


@router.post("/webhook")
def telegram_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
    """Webhook endpoint для Telegram Bot"""
    service = TelegramBotService(db)
    result = service.process_webhook_update(payload.model_dump())
    return {"ok": True, "telegram_response": result}


@router.post("/send-message")
def send_telegram_message(
    payload: SendMessageRequest,
    current_user=Depends(require_permission("marketing.send")),
    db: Session = Depends(get_db),
):
    """Отправить сообщение через Telegram Bot"""
    service = TelegramBotService(db)
    result = service.send_message(payload.chat_id, payload.text)
    return result


@router.get("/webhook-info")
def webhook_info(
    current_user=Depends(require_permission("marketing.read")),
    db: Session = Depends(get_db),
):
    """Информация о webhook"""
    service = TelegramBotService(db)
    return service.get_webhook_info()


@router.post("/setup-webhook")
def setup_webhook(
    webhook_url: str,
    current_user=Depends(require_permission("marketing.create")),
    db: Session = Depends(get_db),
):
    """Установить webhook URL"""
    service = TelegramBotService(db)
    return service.setup_webhook(webhook_url)
