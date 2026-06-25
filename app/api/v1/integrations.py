# app/api/v1/integrations.py
from typing import Optional, List, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.services.integration_service import IntegrationService


router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ========== CONFIGURATION ==========
@router.get("/configs")
async def list_configs(
    club_id: int = Query(...),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Список интеграций клуба"""
    service = IntegrationService(db)
    configs = service.list_integrations(club_id, category)
    
    return [
        {
            "id": str(c.id),
            "provider": c.provider,
            "category": c.category,
            "is_active": c.is_active,
            "sync_status": c.sync_status,
            "last_sync": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "last_error": c.last_error
        }
        for c in configs
    ]


@router.get("/categories")
async def list_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Доступные категории интеграций"""
    return {
        "payments": "Платежи (YooKassa, СБП, Т-Банк, Сбер, АТОЛ)",
        "accounting": "Бухгалтерия (1C, МойСклад)",
        "crm": "CRM (Bitrix24, AmoCRM, RetailCRM)",
        "messaging": "Мессенджеры (Telegram, MAX, WhatsApp)",
        "telephony": "IP-телефония (Манго, Zadarma)",
        "delivery": "Доставка (Яндекс.Еда, СберМаркет)",
        "access_control": "СКУД (ЭРА, Болид, Perco, ZKTeco)",
        "video": "Видеонаблюдение (Hikvision, Dahua, Trassir)",
        "analytics": "Аналитика (Яндекс.Метрика, Google Analytics)",
        "hr": "HR (1C:ЗУП, Каюта)"
    }


@router.post("/configs/{provider}", status_code=201)
async def set_config(
    provider: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("integrations.manage"))
):
    """Настроить интеграцию"""
    service = IntegrationService(db)
    
    club_id = data.get('club_id')
    category = data.get('category')
    config = data.get('config', {})
    is_active = data.get('is_active', False)
    
    if not category:
        raise HTTPException(400, "Category required")
    
    result = service.set_config(club_id, provider, category, config, is_active)
    return {
        "id": str(result.id),
        "provider": result.provider,
        "category": result.category,
        "is_active": result.is_active
    }


@router.post("/configs/{provider}/toggle")
async def toggle_integration(
    provider: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("integrations.manage"))
):
    """Включить/выключить интеграцию"""
    service = IntegrationService(db)
    club_id = data.get('club_id')
    
    config = service.get_config(club_id, provider)
    if not config:
        raise HTTPException(404, "Integration not found")
    
    config.is_active = not config.is_active
    db.commit()
    
    return {
        "provider": provider,
        "is_active": config.is_active
    }


# ========== PAYMENTS ==========
@router.post("/payments/yookassa/create")
async def yookassa_create(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Создать платёж YooKassa"""
    from decimal import Decimal
    
    service = IntegrationService(db)
    club_id = data.get('club_id')
    amount = Decimal(str(data.get('amount', 0)))
    description = data.get('description', 'FitIntel PRO')
    return_url = data.get('return_url', 'https://fixintel.ru/payment/success')
    metadata = data.get('metadata', {})
    
    try:
        result = service.yookassa_create_payment(club_id, amount, description, return_url, metadata)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/payments/sbp/qr")
async def sbp_create_qr(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Создать QR-код СБП"""
    from decimal import Decimal
    
    service = IntegrationService(db)
    club_id = data.get('club_id')
    amount = Decimal(str(data.get('amount', 0)))
    description = data.get('description', 'Оплата через СБП')
    
    try:
        result = service.sbp_create_qr(club_id, amount, description)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/payments/transactions")
async def list_transactions(
    club_id: int = Query(...),
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """История платежей"""
    from app.models.integration import PaymentTransaction
    
    query = db.query(PaymentTransaction).filter(PaymentTransaction.club_id == club_id).order_by(PaymentTransaction.created_at.desc())
    if provider:
        query = query.filter(PaymentTransaction.provider == provider)
    if status:
        query = query.filter(PaymentTransaction.status == status)
    return query.limit(limit).all()


# ========== 1C SYNC ==========
@router.post("/1c/sync")
async def sync_1c(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("integrations.manage"))
):
    """Синхронизация с 1С"""
    service = IntegrationService(db)
    club_id = data.get('club_id')
    direction = data.get('direction', 'out')
    entity = data.get('entity', 'clients')
    
    try:
        result = service.sync_1c(club_id, direction, entity)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ========== CRM ==========
@router.post("/crm/{provider}/lead")
async def send_crm_lead(
    provider: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Отправить лид в CRM"""
    service = IntegrationService(db)
    club_id = data.get('club_id')
    lead_data = data.get('lead_data', {})
    
    try:
        result = service.crm_send_lead(club_id, provider, lead_data)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ========== WEBHOOKS ==========
@router.post("/webhooks/{provider}")
async def receive_webhook(
    provider: str,
    data: dict,
    db: Session = Depends(get_db)
):
    """Получить webhook от провайдера"""
    service = IntegrationService(db)
    
    # Логируем webhook
    headers = {}  # В реальном коде — из request.headers
    signature = headers.get('X-Signature')
    
    log = service.log_webhook(provider, data, headers, signature)
    
    # Обрабатываем асинхронно
    # background_tasks.add_task(service.process_webhook, log.id)
    
    return {
        "received": True,
        "log_id": str(log.id),
        "provider": provider
    }


@router.get("/webhooks/logs")
async def list_webhook_logs(
    provider: Optional[str] = Query(None),
    processed: Optional[bool] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("integrations.read"))
):
    """Логи webhooks"""
    from app.models.integration import WebhookLog
    
    query = db.query(WebhookLog).order_by(WebhookLog.created_at.desc())
    if provider:
        query = query.filter(WebhookLog.provider == provider)
    if processed is not None:
        query = query.filter(WebhookLog.processed == processed)
    return query.limit(limit).all()


# ========== UNIVERSAL API ==========
@router.post("/{provider}/{method}")
async def universal_call(
    provider: str,
    method: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Универсальный вызов метода провайдера"""
    service = IntegrationService(db)
    club_id = data.get('club_id')
    
    try:
        result = service.call_provider(club_id, provider, method, **data)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
