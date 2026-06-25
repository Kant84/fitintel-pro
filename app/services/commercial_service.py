# app/services/commercial_service.py
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.commercial import PricingPlan, PlanModule, ClubSubscription, WhiteLabelConfig
from app.models.client import Client  # заглушка


class CommercialService:
    """Сервис управления тарифами и подписками"""

    def __init__(self, db: Session):
        self.db = db

    # ========== PLANS ==========
    def get_plans(self) -> List[PricingPlan]:
        """Список активных тарифов"""
        return self.db.query(PricingPlan).filter(PricingPlan.is_active == True).all()

    def get_plan(self, plan_id: UUID) -> Optional[PricingPlan]:
        """Тариф по ID"""
        return self.db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()

    def get_plan_by_code(self, code: str) -> Optional[PricingPlan]:
        """Тариф по коду"""
        return self.db.query(PricingPlan).filter(PricingPlan.code == code).first()

    def get_plan_modules(self, plan_id: UUID) -> List[PlanModule]:
        """Модули тарифа"""
        return self.db.query(PlanModule).filter(PlanModule.plan_id == plan_id).all()

    # ========== PRICING ==========
    def calculate_price(self, plan_id: UUID, client_count: int = 0, selected_modules: List[str] = None) -> Dict:
        """Рассчитать стоимость подписки"""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        base = plan.base_price or Decimal("0")
        
        # Динамическая цена по клиентам
        dynamic_price = base
        if plan.max_clients and client_count > plan.max_clients:
            # Переплата за каждого клиента сверх лимита
            overflow = client_count - plan.max_clients
            dynamic_price += Decimal("50") * overflow  # 50 ₽/клиент

        # Дополнительные модули
        module_cost = Decimal("0")
        if selected_modules:
            modules = self.db.query(PlanModule).filter(
                PlanModule.plan_id == plan_id,
                PlanModule.module_code.in_(selected_modules),
                PlanModule.is_included == False
            ).all()
            module_cost = sum(m.price_addon for m in modules)

        total = dynamic_price + module_cost

        # Скидка за годовую оплату
        discount = Decimal("0")
        if plan.billing_cycle == 'yearly':
            discount = total * Decimal("0.15")  # 15% скидка
        elif plan.billing_cycle == 'quarterly':
            discount = total * Decimal("0.05")  # 5% скидка

        return {
            "plan_name": plan.name,
            "base_price": float(base),
            "client_count": client_count,
            "dynamic_price": float(dynamic_price),
            "modules_cost": float(module_cost),
            "discount": float(discount),
            "total": float(total - discount),
            "billing_cycle": plan.billing_cycle
        }

    # ========== SUBSCRIPTIONS ==========
    def create_subscription(self, club_id: int, plan_id: UUID, trial: bool = False) -> ClubSubscription:
        """Создать подписку для клуба"""
        plan = self.get_plan(plan_id)
        
        sub = ClubSubscription(
            club_id=club_id,
            plan_id=plan_id,
            status='trial' if trial else 'active',
            trial_ends_at=datetime.now() + timedelta(days=14) if trial else None,
            current_period_start=datetime.now(),
            current_period_end=datetime.now() + timedelta(days=30),
            next_billing_amount=plan.base_price if plan else 0
        )
        self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def get_subscription(self, club_id: int) -> Optional[ClubSubscription]:
        """Подписка клуба"""
        return self.db.query(ClubSubscription).filter(
            ClubSubscription.club_id == club_id
        ).first()

    def upgrade_plan(self, club_id: int, new_plan_id: UUID) -> ClubSubscription:
        """Апгрейд тарифа"""
        sub = self.get_subscription(club_id)
        if not sub:
            raise ValueError("No active subscription")
        
        old_plan = self.get_plan(sub.plan_id)
        new_plan = self.get_plan(new_plan_id)
        
        # Проратация
        now = datetime.now()
        days_used = (now - sub.current_period_start).days
        days_total = (sub.current_period_end - sub.current_period_start).days
        
        if days_total > 0:
            old_daily = old_plan.base_price / days_total if old_plan else 0
            used_amount = old_daily * days_used
            remaining = old_plan.base_price - used_amount if old_plan else 0
        else:
            remaining = Decimal("0")

        new_price = new_plan.base_price if new_plan else 0
        prorated = max(Decimal("0"), new_price - remaining)

        sub.plan_id = new_plan_id
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30)
        sub.next_billing_amount = prorated
        
        self.db.commit()
        self.db.refresh(sub)
        return sub

    # ========== WHITE LABEL ==========
    def get_white_label(self, club_id: int) -> Optional[WhiteLabelConfig]:
        """White-label конфигурация клуба"""
        return self.db.query(WhiteLabelConfig).filter(
            WhiteLabelConfig.club_id == club_id,
            WhiteLabelConfig.is_active == True
        ).first()

    def set_white_label(self, club_id: int, data: dict) -> WhiteLabelConfig:
        """Настроить white-label"""
        config = self.get_white_label(club_id)
        if not config:
            config = WhiteLabelConfig(club_id=club_id)
            self.db.add(config)
        
        for field, value in data.items():
            if hasattr(config, field):
                setattr(config, field, value)
        
        config.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(config)
        return config

    # ========== FEATURE CHECK ==========
    def check_feature(self, club_id: int, module_code: str) -> bool:
        """Проверить, доступна ли фича для клуба"""
        sub = self.get_subscription(club_id)
        if not sub or sub.status not in ('active', 'trial'):
            return False
        
        # Проверяем модуль в тарифе
        modules = self.db.query(PlanModule).filter(
            PlanModule.plan_id == sub.plan_id,
            PlanModule.module_code == module_code
        ).first()
        
        return modules is not None
