# app/repositories/cash_desk_repository.py

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.cash_desk_session import CashDeskSession
from app.models.cash_operation import CashOperation


class CashDeskRepository:
    """Репозиторий для работы с кассой"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================================
    # СМЕНЫ
    # ==========================================================
    
    def add_session(self, session: CashDeskSession) -> CashDeskSession:
        """Добавить смену"""
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def get_session_by_id(self, session_id: str) -> Optional[CashDeskSession]:
        """Получить смену по ID"""
        return self.db.query(CashDeskSession).filter(CashDeskSession.id == session_id).first()
    
    def get_current_session(self, cashier_user_id: str) -> Optional[CashDeskSession]:
        """Получить текущую открытую смену кассира"""
        return self.db.query(CashDeskSession).filter(
            CashDeskSession.cashier_user_id == cashier_user_id,
            CashDeskSession.status == "OPEN",
        ).first()
    
    def get_last_session_number(self) -> int:
        """Получить последний номер смены"""
        last = self.db.query(CashDeskSession).order_by(
            CashDeskSession.session_number.desc()
        ).first()
        return last.session_number if last else 0
    
    def save_session(self, session: CashDeskSession) -> CashDeskSession:
        """Сохранить изменения смены"""
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def list_sessions(
        self,
        cashier_user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CashDeskSession]:
        """Получить список смен"""
        query = self.db.query(CashDeskSession)
        
        if cashier_user_id:
            query = query.filter(CashDeskSession.cashier_user_id == cashier_user_id)
        
        return query.order_by(CashDeskSession.session_number.desc()).offset(offset).limit(limit).all()
    
    # ==========================================================
    # ОПЕРАЦИИ
    # ==========================================================
    
    def add_operation(self, operation: CashOperation) -> CashOperation:
        """Добавить кассовую операцию"""
        self.db.add(operation)
        self.db.commit()
        self.db.refresh(operation)
        
        # Обновляем итоги смены
        session = self.get_session_by_id(operation.session_id)
        if session:
            if operation.operation_type == "INCOME":
                if operation.payment_method == "CASH":
                    session.cash_income += operation.amount
                else:
                    session.card_income += operation.amount
            else:
                if operation.payment_method == "CASH":
                    session.cash_outcome += operation.amount
            self.db.commit()
        
        return operation
    
    def get_session_operations(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CashOperation]:
        """Получить операции смены"""
        return self.db.query(CashOperation).filter(
            CashOperation.session_id == session_id
        ).order_by(CashOperation.created_at.desc()).offset(offset).limit(limit).all()