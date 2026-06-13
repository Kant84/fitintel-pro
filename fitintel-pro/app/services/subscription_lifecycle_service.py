# app/services/subscription_lifecycle_service.py
from uuid import UUID
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.subscription_event import SubscriptionEvent
from app.models.tariff import Tariff
from app.schemas.enums import SubscriptionStatus


class SubscriptionLifecycleService:
    """
    Сервис управления жизненным циклом абонемента.
    Включает заморозку, разморозку, продление, отмену.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================
    
    def _get_subscription(self, subscription_id: str) -> Subscription:
        """Получить абонемент или выбросить 404"""
        sub = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Абонемент не найден"
            )
        return sub
    
    def _add_status_event(
        self,
        subscription: Subscription,
        to_status: str,
        reason: str | None = None,
        actor_user_id: str | None = None,
    ) -> None:
        """Добавить событие изменения статуса в историю"""
        event = SubscriptionEvent(
            subscription_id=subscription.id,
            from_status=subscription.status,
            to_status=to_status,
            reason=reason,
            actor_user_id=UUID(actor_user_id) if actor_user_id else None,  # ← преобразование
        )
        self.db.add(event)
    
    def _calculate_new_end_date(self, tariff: Tariff, current_end_date: date | None = None) -> date:
        """Рассчитать новую дату окончания на основе тарифа"""
        start = current_end_date if current_end_date and current_end_date > date.today() else date.today()
        return start + timedelta(days=tariff.duration_days)
    
    # ==========================================================
    # ЗАМОРОЗКА
    # ==========================================================
    
    def freeze(
        self,
        subscription_id: str,
        frozen_until: date | None = None,
        reason: str = "OTHER",
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Subscription:
        """
        Заморозить абонемент.
        Только активный абонемент можно заморозить.
        """
        sub = self._get_subscription(subscription_id)
        
        # Проверка: можно заморозить только ACTIVE
        if sub.status != SubscriptionStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Нельзя заморозить абонемент в статусе {sub.status}. Только ACTIVE"
            )
        
        # Проверка: если указана дата, она должна быть в будущем
        if frozen_until and frozen_until <= date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Дата окончания заморозки должна быть в будущем"
            )
        
        # Сохраняем данные заморозки
        sub.frozen_at = datetime.now(timezone.utc)
        sub.frozen_until = frozen_until
        sub.freeze_reason = reason
        
        # Меняем статус
        old_status = sub.status
        sub.status = SubscriptionStatus.FROZEN.value
        
        # Добавляем событие
        self._add_status_event(
            sub,
            sub.status,
            f"Заморозка. Причина: {reason}. {notes if notes else ''}",
            actor_user_id
        )
        
        self.db.commit()
        self.db.refresh(sub)
        
        return sub
    
    # ==========================================================
    # РАЗМОРОЗКА
    # ==========================================================
    
    def unfreeze(
        self,
        subscription_id: str,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Subscription:
        """
        Разморозить абонемент.
        Только замороженный абонемент можно разморозить.
        Дата окончания сдвигается на количество замороженных дней.
        """
        sub = self._get_subscription(subscription_id)
        
        # Проверка: можно разморозить только FROZEN
        if sub.status != SubscriptionStatus.FROZEN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Нельзя разморозить абонемент в статусе {sub.status}. Только FROZEN"
            )
        
        # Проверка: если указана дата окончания заморозки и она прошла
        if sub.frozen_until and sub.frozen_until < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Срок заморозки истёк. Создайте новый абонемент."
            )
        
        # Сдвигаем дату окончания на количество замороженных дней
        if sub.frozen_at:
            frozen_days = (datetime.now(timezone.utc) - sub.frozen_at).days
            if frozen_days > 0:
                sub.end_date = sub.end_date + timedelta(days=frozen_days)
        
        # Очищаем поля заморозки
        sub.frozen_at = None
        sub.frozen_until = None
        sub.freeze_reason = None
        
        # Меняем статус
        sub.status = SubscriptionStatus.ACTIVE.value
        
        # Добавляем событие
        self._add_status_event(
            sub,
            sub.status,
            f"Разморозка. {notes if notes else ''}",
            actor_user_id
        )
        
        self.db.commit()
        self.db.refresh(sub)
        
        return sub
    
    # ==========================================================
    # ПРОДЛЕНИЕ
    # ==========================================================
    
    def renew(
        self,
        subscription_id: str,
        auto_renew: bool | None = None,
        actor_user_id: str | None = None,
    ) -> Subscription:
        """
        Продлить абонемент.
        Можно продлить активный, истекший или замороженный абонемент.
        """
        sub = self._get_subscription(subscription_id)
        
        # Проверка: можно продлить ACTIVE, EXPIRED или FROZEN
        allowed_statuses = [
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.EXPIRED.value,
            SubscriptionStatus.FROZEN.value,
        ]
        if sub.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Нельзя продлить абонемент в статусе {sub.status}"
            )
        
        # Если абонемент замёрз — сначала размораживаем
        if sub.status == SubscriptionStatus.FROZEN.value:
            self.unfreeze(subscription_id, actor_user_id=actor_user_id)
            self.db.refresh(sub)
        
        # Получаем тариф
        tariff = self.db.query(Tariff).filter(Tariff.id == sub.tariff_id).first()
        if not tariff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тариф не найден"
            )
        
        # Рассчитываем новую дату окончания
        old_end_date = sub.end_date if sub.end_date > date.today() else date.today()
        sub.end_date = self._calculate_new_end_date(tariff, old_end_date)
        
        # Обновляем лимиты
        if not tariff.is_unlimited:
            sub.visit_limit = tariff.visit_limit
            sub.visits_used = 0
        
        # Если абонемент был EXPIRED — меняем статус на ACTIVE
        if sub.status == SubscriptionStatus.EXPIRED.value:
            sub.status = SubscriptionStatus.ACTIVE.value
        
        sub.last_renewed_at = datetime.now(timezone.utc)
        
        # Настройка автопродления
        if auto_renew is not None:
            sub.auto_renew = auto_renew
        
        # Добавляем событие
        self._add_status_event(
            sub,
            sub.status,
            f"Продление на {tariff.duration_days} дней. Цена: {tariff.price} {tariff.currency}",
            actor_user_id
        )
        
        self.db.commit()
        self.db.refresh(sub)
        
        return sub
    
    # ==========================================================
    # ОТМЕНА
    # ==========================================================
    
    def cancel(
        self,
        subscription_id: str,
        reason: str = "USER_REQUEST",
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Subscription:
        """
        Отменить абонемент.
        Можно отменить активный или замороженный абонемент.
        """
        sub = self._get_subscription(subscription_id)
        
        # Проверка: можно отменить ACTIVE или FROZEN
        allowed_statuses = [
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.FROZEN.value,
        ]
        if sub.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Нельзя отменить абонемент в статусе {sub.status}"
            )
        
        sub.cancelled_at = datetime.now(timezone.utc)
        sub.cancellation_reason = reason
        sub.is_active = False
        
        # Меняем статус
        sub.status = SubscriptionStatus.CANCELLED.value
        
        # Добавляем событие
        self._add_status_event(
            sub,
            sub.status,
            f"Отмена. Причина: {reason}. {notes if notes else ''}",
            actor_user_id
        )
        
        self.db.commit()
        self.db.refresh(sub)
        
        return sub
    
    # ==========================================================
    # ИСТОРИЯ СТАТУСОВ
    # ==========================================================
    
    def get_status_history(
        self,
        subscription_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Получить историю изменений статуса абонемента.
        """
        # Проверяем существование абонемента
        self._get_subscription(subscription_id)
        
        events = (
            self.db.query(SubscriptionEvent)
            .filter(SubscriptionEvent.subscription_id == subscription_id)
            .order_by(SubscriptionEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return {
            "items": events,
            "count": len(events),
        }
    
    # ==========================================================
    # ФОНОВАЯ ЗАДАЧА: ПРОВЕРКА ИСТЕКШИХ АБОНЕМЕНТОВ
    # ==========================================================
    
    def expire_expired_subscriptions(self) -> int:
        """
        Обновить статус истекших абонементов.
        Вызывается из Celery (фоновая задача).
        """
        expired_subs = (
            self.db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.end_date < date.today(),
            )
            .all()
        )
        
        count = 0
        for sub in expired_subs:
            sub.status = SubscriptionStatus.EXPIRED.value
            sub.is_active = False
            self._add_status_event(
                sub,
                sub.status,
                "Автоматическое истечение срока",
                actor_user_id=None
            )
            count += 1
        
        self.db.commit()
        return count