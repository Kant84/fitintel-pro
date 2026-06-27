# app/services/cash_desk_service.py

from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cash_desk_session import CashDeskSession
from app.models.cash_operation import CashOperation
from app.models.user import User
from app.repositories.cash_desk_repository import CashDeskRepository
from app.services.audit_service import AuditService
from app.schemas.cash_desk import (
    CashDeskOpenRequest,
    CashDeskCloseRequest,
    CashDeskSessionResponse,
    CashDeskSessionListResponse,
    CashDeskCurrentResponse,
    CashOperationCreateRequest,
    CashOperationResponse,
    CashOperationListResponse,
)
from app.schemas.enums import CashOperationType, PaymentMethod, CashDeskStatus


class CashDeskService:
    """
    Сервис для управления кассовыми сменами и операциями.
    
    Включает:
    - Открытие/закрытие смены
    - Учёт кассовых операций
    - Z-отчёты
    - Сверку наличных
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = CashDeskRepository(db)
        self.audit = AuditService(db)
    
    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================
    
    def _get_user(self, user_id: str) -> User:
        """Получить пользователя или выбросить 404"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        return user
    
    def _get_session(self, session_id: str) -> CashDeskSession:
        """Получить смену или выбросить 404"""
        session = self.repository.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Смена не найдена"
            )
        return session
    
    def _get_current_session(self, cashier_user_id: str) -> CashDeskSession:
        """Получить текущую открытую смену кассира"""
        session = self.repository.get_current_session(cashier_user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Нет открытой смены. Откройте смену перед выполнением операций."
            )
        if session.status != CashDeskStatus.OPEN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Смена уже закрыта"
            )
        return session
    
    def _build_session_response(self, session: CashDeskSession) -> dict:
        """Построить ответ смены"""
        cashier = self._get_user(session.cashier_user_id)
        return {
            "id": session.id,
            "session_number": session.session_number,
            "cashier_user_id": session.cashier_user_id,
            "cashier_name": cashier.username if cashier else None,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
            "opening_balance": session.opening_balance,
            "closing_balance": session.closing_balance,
            "cash_income": session.cash_income,
            "cash_outcome": session.cash_outcome,
            "card_income": session.card_income,
            "expected_cash": session.expected_cash,
            "actual_cash": session.actual_cash,
            "discrepancy": session.discrepancy,
            "status": session.status,
            "notes": session.notes,
            "created_at": session.created_at,
        }
    
    def _build_operation_response(self, operation: CashOperation) -> dict:
        """Построить ответ кассовой операции"""
        return {
            "id": operation.id,
            "session_id": operation.session_id,
            "operation_type": operation.operation_type,
            "amount": operation.amount,
            "payment_method": operation.payment_method,
            "reference_type": operation.reference_type,
            "reference_id": operation.reference_id,
            "description": operation.description,
            "created_by_user_id": operation.created_by_user_id,
            "created_at": operation.created_at,
        }
    
    # ==========================================================
    # УПРАВЛЕНИЕ СМЕНАМИ
    # ==========================================================
    
    def open_session(
        self,
        cashier_user_id: str,
        opening_balance: Decimal = Decimal("0.00"),
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> CashDeskSession:
        """
        Открыть кассовую смену.
        
        Args:
            cashier_user_id: ID кассира
            opening_balance: Начальный остаток в кассе
            notes: Заметки
            actor_user_id: Кто выполняет операцию
        
        Returns:
            Открытая смена
        """
        # Проверяем, нет ли уже открытой смены у этого кассира

        existing = self.repository.get_current_session(cashier_user_id)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"У кассира уже есть открытая смена #{existing.session_number}"
            )
        
        # Проверяем, нет ли открытой смены у другого кассира
        any_open = self.repository.get_any_open_session()
        if any_open and str(any_open.cashier_user_id) != str(cashier_user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Смена уже открыта другим кассиром #{any_open.session_number}"
            )
        
        # Получаем последний номер смены
        last_number = self.repository.get_last_session_number()
        new_number = last_number + 1
        
        session = CashDeskSession(
            session_number=new_number,
            cashier_user_id=cashier_user_id,
            opened_at=datetime.now(),
            opening_balance=opening_balance,
            cash_income=Decimal("0.00"),
            cash_outcome=Decimal("0.00"),
            card_income=Decimal("0.00"),
            status=CashDeskStatus.OPEN.value,
            notes=notes,
        )
        
        created_session = self.repository.add_session(session)
        
        self.audit.log(
            action="cash_desk.opened",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="cash_desk_session",
            entity_id=created_session.id,
            message=f"Cash desk session #{new_number} opened by cashier {cashier_user_id}",
            after_data={
                "session_number": new_number,
                "opening_balance": str(opening_balance),
            },
        )
        
        return created_session
    
    def close_session(
        self,
        cashier_user_id: str,
        actual_cash: Decimal,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> CashDeskSession:
        """
        Закрыть кассовую смену с Z-отчётом.
        
        Args:
            cashier_user_id: ID кассира
            actual_cash: Фактическая наличность в кассе
            notes: Заметки
            actor_user_id: Кто выполняет операцию
        
        Returns:
            Закрытая смена
        """
        session = self._get_current_session(cashier_user_id)
        
        # Рассчитываем ожидаемую наличность
        expected_cash = session.opening_balance + session.cash_income - session.cash_outcome
        
        # Рассчитываем расхождение
        discrepancy = actual_cash - expected_cash
        
        session.closed_at = datetime.now()
        session.closing_balance = actual_cash
        session.expected_cash = expected_cash
        session.actual_cash = actual_cash
        session.discrepancy = discrepancy
        session.status = CashDeskStatus.CLOSED.value
        if notes:
            session.notes = f"{session.notes or ''}\n{notes}".strip()
        
        closed_session = self.repository.save_session(session)
        
        self.audit.log(
            action="cash_desk.closed",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="cash_desk_session",
            entity_id=session.id,
            message=f"Cash desk session #{session.session_number} closed",
            after_data={
                "session_number": session.session_number,
                "expected_cash": str(expected_cash),
                "actual_cash": str(actual_cash),
                "discrepancy": str(discrepancy),
            },
        )
        
        return closed_session
    
    def get_current_session(self, cashier_user_id: str) -> CashDeskCurrentResponse:
        """Получить текущую открытую смену"""
        session = self.repository.get_current_session(cashier_user_id)
        
        if not session:
            return CashDeskCurrentResponse(
                has_open_session=False,
                session=None,
            )
        
        return CashDeskCurrentResponse(
            has_open_session=True,
            session=self._build_session_response(session),
        )
    
    def get_session(self, session_id: str) -> CashDeskSession:
        """Получить смену по ID"""
        return self._get_session(session_id)
    
    def list_sessions(
        self,
        cashier_user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CashDeskSessionListResponse:
        """Получить список смен"""
        sessions = self.repository.list_sessions(
            cashier_user_id=cashier_user_id,
            limit=limit,
            offset=offset,
        )
        
        total_cash_income = Decimal("0.00")
        total_card_income = Decimal("0.00")
        
        for s in sessions:
            total_cash_income += s.cash_income
            total_card_income += s.card_income
        
        return CashDeskSessionListResponse(
            items=[self._build_session_response(s) for s in sessions],
            count=len(sessions),
            total_cash_income=total_cash_income,
            total_card_income=total_card_income,
        )
    
    # ==========================================================
    # КАССОВЫЕ ОПЕРАЦИИ
    # ==========================================================
    
    def add_operation(
        self,
        cashier_user_id: str,
        operation_type: CashOperationType,
        amount: Decimal,
        payment_method: PaymentMethod,
        reference_type: str | None = None,
        reference_id: str | None = None,
        description: str | None = None,
        actor_user_id: str | None = None,
    ) -> CashOperation:
        """
        Добавить кассовую операцию (приход/расход).
        
        Args:
            cashier_user_id: ID кассира
            operation_type: Тип операции (INCOME, OUTCOME)
            amount: Сумма
            payment_method: Способ оплаты (CASH, CARD)
            reference_type: Тип связанной сущности
            reference_id: ID связанной сущности
            description: Описание
            actor_user_id: Кто выполняет операцию
        
        Returns:
            Созданная операция
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма операции должна быть положительной"
            )
        
        # Получаем текущую открытую смену
        session = self._get_current_session(cashier_user_id)
        
        # Проверяем баланс для расходных операций
        if operation_type.value in ["WITHDRAWAL", "EXPENSE"]:
            from sqlalchemy import func
            from app.models.cash_operation import CashOperation as CashOpModel
            total_income = self.db.query(func.sum(CashOpModel.amount)).filter(
                CashOpModel.session_id == session.id,
                CashOpModel.operation_type.in_(["DEPOSIT", "INCOME"])
            ).scalar() or Decimal("0")
            total_outcome = self.db.query(func.sum(CashOpModel.amount)).filter(
                CashOpModel.session_id == session.id,
                CashOpModel.operation_type.in_(["WITHDRAWAL", "EXPENSE"])
            ).scalar() or Decimal("0")
            balance = total_income - total_outcome
            if amount > balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недостаточно средств в кассе. Баланс: {balance}, запрошено: {amount}"
                )
        
        operation = CashOperation(
            session_id=session.id,
            operation_type=operation_type.value,
            amount=amount,
            payment_method=payment_method.value,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            created_by_user_id=actor_user_id,
        )
        
        created_operation = self.repository.add_operation(operation)
        
        # Обновляем итоги смены (уже в репозитории)
        
        self.audit.log(
            action="cash_desk.operation",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="cash_operation",
            entity_id=created_operation.id,
            message=f"Cash operation: {operation_type.value} {amount} {payment_method.value}",
            after_data={
                "session_number": session.session_number,
                "operation_type": operation_type.value,
                "amount": str(amount),
                "payment_method": payment_method.value,
            },
        )
        
        return created_operation
    
    def get_session_operations(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> CashOperationListResponse:
        """Получить операции смены"""
        session = self._get_session(session_id)
        
        operations = self.repository.get_session_operations(
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
        
        total_income = Decimal("0.00")
        total_outcome = Decimal("0.00")
        
        for op in operations:
            if op.operation_type == CashOperationType.INCOME.value:
                total_income += op.amount
            else:
                total_outcome += op.amount
        
        return CashOperationListResponse(
            items=[self._build_operation_response(op) for op in operations],
            count=len(operations),
            total_income=total_income,
            total_outcome=total_outcome,
        )
    
    # ==========================================================
    # ОТЧЁТЫ
    # ==========================================================
    
    def get_z_report(self, session_id: str) -> dict:
        """
        Сформировать Z-отчёт по смене.
        
        Returns:
            Словарь с отчётом
        """
        session = self._get_session(session_id)
        cashier = self._get_user(session.cashier_user_id)
        operations = self.repository.get_session_operations(session_id, limit=10000)
        
        # Группируем операции по типу и способу оплаты
        cash_income_ops = []
        cash_outcome_ops = []
        card_income_ops = []
        
        for op in operations:
            if op.operation_type == CashOperationType.INCOME.value:
                if op.payment_method == PaymentMethod.CASH.value:
                    cash_income_ops.append(op)
                else:
                    card_income_ops.append(op)
            else:
                if op.payment_method == PaymentMethod.CASH.value:
                    cash_outcome_ops.append(op)
        
        report = {
            "session_number": session.session_number,
            "cashier": cashier.username if cashier else None,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
            "opening_balance": float(session.opening_balance),
            "closing_balance": float(session.closing_balance) if session.closing_balance else None,
            "cash_income": float(session.cash_income),
            "cash_outcome": float(session.cash_outcome),
            "card_income": float(session.card_income),
            "expected_cash": float(session.expected_cash) if session.expected_cash else None,
            "actual_cash": float(session.actual_cash) if session.actual_cash else None,
            "discrepancy": float(session.discrepancy) if session.discrepancy else None,
            "operations": {
                "cash_income": [
                    {
                        "amount": float(op.amount),
                        "description": op.description,
                        "reference_type": op.reference_type,
                        "reference_id": op.reference_id,
                        "created_at": op.created_at,
                    }
                    for op in cash_income_ops
                ],
                "cash_outcome": [
                    {
                        "amount": float(op.amount),
                        "description": op.description,
                        "created_at": op.created_at,
                    }
                    for op in cash_outcome_ops
                ],
                "card_income": [
                    {
                        "amount": float(op.amount),
                        "description": op.description,
                        "created_at": op.created_at,
                    }
                    for op in card_income_ops
                ],
            },
            "total_operations": len(operations),
        }
        
        return report
    
    # ==========================================================
    # СВЕРКА
    # ==========================================================
    
    def verify_cash(
        self,
        cashier_user_id: str,
        actual_cash: Decimal,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> dict:
        """
        Промежуточная сверка наличных (без закрытия смены).
        
        Args:
            cashier_user_id: ID кассира
            actual_cash: Фактическая наличность
            notes: Заметки
        
        Returns:
            Результат сверки
        """
        session = self._get_current_session(cashier_user_id)
        
        expected_cash = session.opening_balance + session.cash_income - session.cash_outcome
        discrepancy = actual_cash - expected_cash
        
        self.audit.log(
            action="cash_desk.verify",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="cash_desk_session",
            entity_id=session.id,
            message=f"Cash verification for session #{session.session_number}",
            after_data={
                "expected_cash": str(expected_cash),
                "actual_cash": str(actual_cash),
                "discrepancy": str(discrepancy),
            },
        )
        
        return {
            "session_number": session.session_number,
            "expected_cash": expected_cash,
            "actual_cash": actual_cash,
            "discrepancy": discrepancy,
            "is_match": discrepancy == 0,
            "notes": notes,
        }