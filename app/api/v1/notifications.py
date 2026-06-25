# app/api/v1/notifications.py
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ========== PUSH SUBSCRIPTIONS ==========
@router.post("/push/subscribe", status_code=201)
async def subscribe_push(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Подписка на Web Push уведомления"""
    from app.models.notification import PushSubscription
    
    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=data.get('endpoint'),
        p256dh=data.get('p256dh'),
        auth=data.get('auth')
    )
    db.add(sub)
    db.commit()
    return {"status": "subscribed"}


@router.delete("/push/unsubscribe", status_code=204)
async def unsubscribe_push(
    endpoint: str = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Отписка от Web Push"""
    from app.models.notification import PushSubscription
    
    db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.endpoint == endpoint
    ).delete()
    db.commit()
    return None


# ========== SEND NOTIFICATIONS ==========
@router.post("/send", status_code=200)
async def send_notification(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("notifications.send"))
):
    """Отправка уведомления с fallback"""
    service = NotificationService(db)
    
    user_id = data.get('user_id')
    message = data.get('message')
    subject = data.get('subject')
    priority = data.get('priority', 'high')
    channels = data.get('channels')
    
    results = service.send_with_fallback(
        user_id=user_id,
        message=message,
        subject=subject,
        priority=priority,
        channels=channels
    )
    
    return {
        "results": results,
        "user_id": user_id,
        "priority": priority
    }


# ========== MAX MESSENGER ==========
@router.post("/max/send", status_code=200)
async def send_max_message(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("notifications.send"))
):
    """Отправка через MAX Messenger"""
    service = NotificationService(db)
    
    user_id = data.get('user_id')
    message = data.get('message')
    
    result = service.send_max_message(user_id, message)
    return {"max_sent": result, "user_id": user_id}


# ========== EMAIL ==========
@router.post("/email/send", status_code=200)
async def send_email(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("notifications.send"))
):
    """Отправка email"""
    service = NotificationService(db)
    
    to_email = data.get('to_email')
    subject = data.get('subject')
    body = data.get('body')
    template_name = data.get('template')
    
    if template_name:
        subject, body = service.render_template(template_name, data.get('variables', {}))
        if not body:
            raise HTTPException(404, "Template not found")
    
    result = service.send_email(to_email, subject, body)
    return {"email_sent": result, "to": to_email}


# ========== SMS ==========
@router.post("/sms/send", status_code=200)
async def send_sms(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("notifications.send"))
):
    """Отправка SMS"""
    service = NotificationService(db)
    
    phone = data.get('phone')
    message = data.get('message')
    
    result = service.send_sms(phone, message)
    return {"sms_sent": result, "phone": phone}


# ========== TELEGRAM ==========
@router.post("/telegram/send", status_code=200)
async def send_telegram(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("notifications.send"))
):
    """Отправка через Telegram Bot"""
    service = NotificationService(db)
    
    chat_id = data.get('chat_id')
    message = data.get('message')
    
    result = service.send_telegram(chat_id, message)
    return {"telegram_sent": result, "chat_id": chat_id}


# ========== TEMPLATES ==========
@router.get("/templates")
async def list_templates(
    channel: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Список шаблонов уведомлений"""
    from app.models.notification import NotificationTemplate
    
    query = db.query(NotificationTemplate).filter(NotificationTemplate.is_active == True)
    if channel:
        query = query.filter(NotificationTemplate.channel == channel)
    return query.all()


@router.post("/templates", status_code=201)
async def create_template(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("notifications.manage"))
):
    """Создать шаблон уведомления"""
    from app.models.notification import NotificationTemplate
    
    template = NotificationTemplate(**data)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


# ========== LOGS ==========
@router.get("/logs")
async def get_logs(
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("notifications.read"))
):
    """История отправки уведомлений"""
    from app.models.notification import NotificationLog
    
    query = db.query(NotificationLog).order_by(NotificationLog.created_at.desc())
    if channel:
        query = query.filter(NotificationLog.channel == channel)
    if status:
        query = query.filter(NotificationLog.status == status)
    return query.limit(limit).all()
