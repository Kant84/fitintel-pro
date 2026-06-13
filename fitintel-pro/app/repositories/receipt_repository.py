# app/repositories/receipt_repository.py

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.receipt import Receipt


class ReceiptRepository:
    """Репозиторий для работы с чеками"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, receipt: Receipt) -> Receipt:
        """Добавить чек"""
        self.db.add(receipt)
        self.db.commit()
        self.db.refresh(receipt)
        return receipt
    
    def get_by_id(self, receipt_id: str) -> Optional[Receipt]:
        """Получить чек по ID"""
        return self.db.query(Receipt).filter(Receipt.id == receipt_id).first()
    
    def get_by_payment_id(self, payment_id: str) -> Optional[Receipt]:
        """Получить чек по ID платежа"""
        return self.db.query(Receipt).filter(Receipt.payment_id == payment_id).first()
    
    def get_by_number(self, receipt_number: str) -> Optional[Receipt]:
        """Получить чек по номеру"""
        return self.db.query(Receipt).filter(Receipt.receipt_number == receipt_number).first()
    
    def save(self, receipt: Receipt) -> Receipt:
        """Сохранить изменения"""
        self.db.commit()
        self.db.refresh(receipt)
        return receipt
    
    def mark_as_sent(self, receipt_id: str) -> Optional[Receipt]:
        """Отметить чек как отправленный"""
        receipt = self.get_by_id(receipt_id)
        if receipt:
            receipt.is_sent = True
            self.db.commit()
            self.db.refresh(receipt)
        return receipt