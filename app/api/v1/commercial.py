# app/api/v1/commercial.py
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.services.commercial_service import CommercialService


router = APIRouter(prefix="/commercial", tags=["Commercial"])


# ========== PLANS ==========
@router.get("/plans")
async def list_plans(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Список тарифных планов"""
    service = CommercialService(db)
    plans = service.get_plans()
    
    result = []
    for plan in plans:
        modules = service.get_plan_modules(plan.id)
        result.append({
            "id": str(plan.id),
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "base_price": float(plan.base_price),
            "billing_cycle": plan.billing_cycle,
            "max_clients": plan.max_clients,
            "max_trainers": plan.max_trainers,
            "max_clubs": plan.max_clubs,
            "modules": [
                {
                    "code": m.module_code,
                    "name": m.module_name,
                    "included": m.is_included,
                    "price_addon": float(m.price_addon) if m.price_addon else 0
                }
                for m in modules
            ]
        })
    
    return result


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Тариф по ID"""
    service = CommercialService(db)
    plan = service.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    
    modules = service.get_plan_modules(plan_id)
    return {
        "id": str(plan.id),
        "code": plan.code,
        "name": plan.name,
        "base_price": float(plan.base_price),
        "modules": modules
    }


@router.post("/plans/{plan_id}/calculate")
async def calculate_price(
    plan_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Рассчитать стоимость"""
    service = CommercialService(db)
    client_count = data.get('client_count', 0)
    modules = data.get('modules', [])
    
    result = service.calculate_price(plan_id, client_count, modules)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ========== SUBSCRIPTIONS ==========
@router.post("/subscribe", status_code=201)
async def create_subscription(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("commercial.manage"))
):
    """Оформить подписку"""
    service = CommercialService(db)
    
    club_id = data.get('club_id')
    plan_id = data.get('plan_id')
    trial = data.get('trial', False)
    
    # Проверяем, нет ли уже подписки
    existing = service.get_subscription(club_id)
    if existing:
        raise HTTPException(400, "Subscription already exists, use upgrade")
    
    sub = service.create_subscription(club_id, plan_id, trial)
    return {
        "id": str(sub.id),
        "status": sub.status,
        "trial_ends": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None
    }


@router.get("/subscriptions/{club_id}")
async def get_subscription(
    club_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Подписка клуба"""
    service = CommercialService(db)
    sub = service.get_subscription(club_id)
    if not sub:
        raise HTTPException(404, "No subscription found")
    
    plan = service.get_plan(sub.plan_id)
    return {
        "id": str(sub.id),
        "plan": plan.name if plan else None,
        "status": sub.status,
        "trial_ends": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "next_billing": float(sub.next_billing_amount) if sub.next_billing_amount else 0,
        "auto_renew": sub.auto_renew
    }


@router.post("/subscriptions/{club_id}/upgrade")
async def upgrade_subscription(
    club_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("commercial.manage"))
):
    """Апгрейд тарифа"""
    service = CommercialService(db)
    new_plan_id = data.get('plan_id')
    
    try:
        sub = service.upgrade_plan(club_id, new_plan_id)
        return {
            "id": str(sub.id),
            "new_plan_id": str(sub.plan_id),
            "next_billing": float(sub.next_billing_amount) if sub.next_billing_amount else 0,
            "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


# ========== WHITE LABEL ==========
@router.get("/white-label/{club_id}")
async def get_white_label(
    club_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """White-label конфигурация"""
    service = CommercialService(db)
    config = service.get_white_label(club_id)
    if not config:
        raise HTTPException(404, "White-label not configured")
    return config


@router.post("/white-label/{club_id}", status_code=201)
async def set_white_label(
    club_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("commercial.manage"))
):
    """Настроить white-label"""
    service = CommercialService(db)
    config = service.set_white_label(club_id, data)
    return {
        "club_id": club_id,
        "app_name": config.app_name,
        "primary_color": config.primary_color,
        "logo_url": config.logo_url
    }


# ========== FEATURE CHECK ==========
@router.get("/features/{club_id}")
async def check_features(
    club_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Проверка доступных фич для клуба"""
    service = CommercialService(db)
    
    # Все возможные модули
    all_modules = ['crm', 'schedule', 'scud', 'payments', 'analytics', 'trainers', 'warehouse', 'multiclub']
    
    features = {}
    for module in all_modules:
        features[module] = service.check_feature(club_id, module)
    
    sub = service.get_subscription(club_id)
    plan = service.get_plan(sub.plan_id) if sub else None
    
    return {
        "club_id": club_id,
        "plan": plan.code if plan else None,
        "status": sub.status if sub else None,
        "features": features
    }
