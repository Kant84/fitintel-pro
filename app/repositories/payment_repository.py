# app/repositories/payment_repository.py

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.payment import Payment


class PaymentRepository:
    """Репозиторий для работы с платежами"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, payment: Payment) -> Payment:
        """Добавить платёж"""
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment
    
    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Получить платёж по ID"""
        return self.db.query(Payment).filter(Payment.id == payment_id).first()
    
    def get_by_external_id(self, external_id: str) -> Optional[Payment]:
        """Получить платёж по внешнему ID"""
        return self.db.query(Payment).filter(Payment.external_payment_id == external_id).first()
    
    def save(self, payment: Payment) -> Payment:
        """Сохранить изменения"""
        self.db.commit()
        self.db.refresh(payment)
        return payment
    
    def list_by_client(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> List[Payment]:
        """Получить платежи клиента"""
        query = self.db.query(Payment).filter(Payment.client_id == client_id)
        
        if status:
            query = query.filter(Payment.status == status)
        
        return query.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_status(
        self,
        payment_id: str,
        status: str,
        external_payment_id: str | None = None,
        paid_at: datetime | None = None,
    ) -> Optional[Payment]:
        """Обновить статус платежа"""
        payment = self.get_by_id(payment_id)
        if payment:
            payment.status = status
            if external_payment_id:
                payment.external_payment_id = external_payment_id
            if paid_at:
                payment.paid_at = paid_at
            self.db.commit()
            self.db.refresh(payment)
        return payment