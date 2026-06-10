# app/services/wallet_service.py

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.client import Client
from app.repositories.wallet_repository import WalletRepository
from app.services.audit_service import AuditService
from app.schemas.wallet import (
    WalletResponse,
    WalletTransactionResponse,
    WalletTransactionListResponse,
    WalletDepositRequest,
    WalletDepositResponse,
)
from app.schemas.enums import TransactionType, PaymentMethod


class WalletService:
    """
    Сервис для управления кошельком клиента.
    
    Включает:
    - Пополнение баланса
    - Списание средств
    - Заморозку/разморозку средств
    - История транзакций
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = WalletRepository(db)
        self.audit = AuditService(db)
    
    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================
    
    def _get_client(self, client_id: str) -> Client:
        """Получить клиента или выбросить 404"""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден"
            )
        return client
    
    def _get_wallet(self, client_id: str, create_if_missing: bool = True) -> Wallet:
        """
        Получить кошелёк клиента.
        Если кошелька нет и create_if_missing=True — создаёт новый.
        """
        wallet = self.repository.get_by_client_id(client_id)
        
        if not wallet and create_if_missing:
            wallet = self.repository.create(client_id)
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кошелёк не найден"
            )
        
        return wallet
    
    def _add_transaction(
        self,
        wallet_id: str,
        transaction_type: str,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        description: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        created_by_user_id: str | None = None,
    ) -> WalletTransaction:
        """Добавить транзакцию в историю"""
        transaction = WalletTransaction(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by_user_id=created_by_user_id,
        )
        return self.repository.add_transaction(transaction)
    
    def _update_balance(
        self,
        wallet: Wallet,
        new_balance: Decimal,
        transaction_type: str,
        amount: Decimal,
        description: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        actor_user_id: str | None = None,
    ) -> Tuple[Wallet, WalletTransaction]:
        """
        Обновить баланс и создать транзакцию.
        
        Returns:
            (wallet, transaction)
        """
        old_balance = wallet.balance
        
        wallet.balance = new_balance
        wallet = self.repository.save(wallet)
        
        transaction = self._add_transaction(
            wallet_id=wallet.id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=old_balance,
            balance_after=new_balance,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by_user_id=actor_user_id,
        )
        
        return wallet, transaction
    
    # ==========================================================
    # ПОЛУЧЕНИЕ ИНФОРМАЦИИ
    # ==========================================================
    
    def get_wallet(self, client_id: str) -> Wallet:
        """Получить кошелёк клиента"""
        return self._get_wallet(client_id)
    
    def get_balance(self, client_id: str) -> dict:
        """Получить баланс клиента"""
        wallet = self._get_wallet(client_id, create_if_missing=False)
        
        return {
            "client_id": client_id,
            "balance": wallet.balance,
            "currency": wallet.currency,
            "frozen_balance": wallet.frozen_balance,
            "available_balance": wallet.balance - wallet.frozen_balance,
        }
    
    def get_transactions(
        self,
        client_id: str,
        transaction_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        reference_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> WalletTransactionListResponse:
        """Получить историю транзакций клиента"""
        wallet = self._get_wallet(client_id, create_if_missing=False)
        
        query = self.db.query(WalletTransaction).filter(
            WalletTransaction.wallet_id == wallet.id
        )
        
        if transaction_type:
            query = query.filter(WalletTransaction.transaction_type == transaction_type)
        
        if start_date:
            query = query.filter(WalletTransaction.created_at >= start_date)
        
        if end_date:
            query = query.filter(WalletTransaction.created_at <= end_date)
        
        if reference_type:
            query = query.filter(WalletTransaction.reference_type == reference_type)
        
        total_count = query.count()
        transactions = query.order_by(
            WalletTransaction.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Считаем суммы пополнений и списаний
        total_deposited = Decimal("0.00")
        total_withdrawn = Decimal("0.00")
        
        for t in transactions:
            if t.transaction_type == TransactionType.DEPOSIT.value:
                total_deposited += t.amount
            elif t.transaction_type == TransactionType.WITHDRAW.value:
                total_withdrawn += t.amount
        
        return WalletTransactionListResponse(
            items=[self._build_transaction_response(t) for t in transactions],
            count=total_count,
            total_deposited=total_deposited,
            total_withdrawn=total_withdrawn,
        )
    
    def _build_transaction_response(self, transaction: WalletTransaction) -> dict:
        """Построить ответ транзакции"""
        return {
            "id": transaction.id,
            "wallet_id": transaction.wallet_id,
            "transaction_type": transaction.transaction_type,
            "amount": transaction.amount,
            "balance_before": transaction.balance_before,
            "balance_after": transaction.balance_after,
            "description": transaction.description,
            "reference_type": transaction.reference_type,
            "reference_id": transaction.reference_id,
            "created_by_user_id": transaction.created_by_user_id,
            "created_at": transaction.created_at,
        }
    
    # ==========================================================
    # ПОПОЛНЕНИЕ
    # ==========================================================
    
    def deposit(
        self,
        client_id: str,
        amount: Decimal,
        payment_method: str,
        notes: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        actor_user_id: str | None = None,
    ) -> WalletDepositResponse:
        """
        Пополнить баланс клиента.
        
        Args:
            client_id: ID клиента
            amount: Сумма пополнения
            payment_method: Способ оплаты (CASH, CARD, ONLINE, SBP)
            notes: Заметки
            reference_type: Тип связанной сущности (payment, etc.)
            reference_id: ID связанной сущности
            actor_user_id: Кто выполнил операцию
        
        Returns:
            Результат пополнения
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма пополнения должна быть положительной"
            )
        
        client = self._get_client(client_id)
        wallet = self._get_wallet(client_id)
        
        old_balance = wallet.balance
        new_balance = old_balance + amount
        
        wallet, transaction = self._update_balance(
            wallet=wallet,
            new_balance=new_balance,
            transaction_type=TransactionType.DEPOSIT.value,
            amount=amount,
            description=f"Пополнение баланса на {amount} {wallet.currency}. Способ: {payment_method}. {notes or ''}",
            reference_type=reference_type,
            reference_id=reference_id,
            actor_user_id=actor_user_id,
        )
        
        # Логируем
        self.audit.log(
            action="wallet.deposit",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="wallet",
            entity_id=wallet.id,
            message=f"Wallet deposit for client {client.email}: {amount} {wallet.currency}",
            after_data={
                "client_id": client_id,
                "amount": str(amount),
                "payment_method": payment_method,
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
            },
        )
        
        return WalletDepositResponse(
            success=True,
            wallet_id=wallet.id,
            new_balance=new_balance,
            transaction_id=transaction.id,
            message=f"Баланс пополнен на {amount} {wallet.currency}",
        )
    
    # ==========================================================
    # СПИСАНИЕ
    # ==========================================================
    
    def withdraw(
        self,
        client_id: str,
        amount: Decimal,
        description: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
        actor_user_id: str | None = None,
        allow_negative: bool = False,
    ) -> Tuple[Wallet, WalletTransaction]:
        """
        Списать средства с баланса клиента.
        
        Args:
            client_id: ID клиента
            amount: Сумма списания
            description: Описание списания
            reference_type: Тип связанной сущности
            reference_id: ID связанной сущности
            actor_user_id: Кто выполнил операцию
            allow_negative: Разрешить отрицательный баланс
        
        Returns:
            (wallet, transaction)
        
        Raises:
            HTTPException: Если недостаточно средств
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма списания должна быть положительной"
            )
        
        client = self._get_client(client_id)
        wallet = self._get_wallet(client_id)
        
        available_balance = wallet.balance - wallet.frozen_balance
        
        if available_balance < amount and not allow_negative:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостаточно средств. Доступно: {available_balance} {wallet.currency}"
            )
        
        old_balance = wallet.balance
        new_balance = old_balance - amount
        
        wallet, transaction = self._update_balance(
            wallet=wallet,
            new_balance=new_balance,
            transaction_type=TransactionType.WITHDRAW.value,
            amount=amount,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            actor_user_id=actor_user_id,
        )
        
        # Логируем
        self.audit.log(
            action="wallet.withdraw",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="wallet",
            entity_id=wallet.id,
            message=f"Wallet withdrawal for client {client.email}: {amount} {wallet.currency}",
            after_data={
                "client_id": client_id,
                "amount": str(amount),
                "description": description,
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
            },
        )
        
        return wallet, transaction
    
    # ==========================================================
    # ЗАМОРОЗКА / РАЗМОРОЗКА
    # ==========================================================
    
    def freeze(
        self,
        client_id: str,
        amount: Decimal,
        reason: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
        actor_user_id: str | None = None,
    ) -> Tuple[Wallet, WalletTransaction]:
        """
        Заморозить средства на балансе (для спорных операций, возвратов).
        
        Замороженные средства недоступны для списания.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма заморозки должна быть положительной"
            )
        
        wallet = self._get_wallet(client_id)
        available_balance = wallet.balance - wallet.frozen_balance
        
        if available_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостаточно средств для заморозки. Доступно: {available_balance} {wallet.currency}"
            )
        
        old_frozen = wallet.frozen_balance
        wallet.frozen_balance += amount
        wallet = self.repository.save(wallet)
        
        transaction = self._add_transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.FREEZE.value,
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            description=f"Заморозка средств: {reason}",
            reference_type=reference_type,
            reference_id=reference_id,
            created_by_user_id=actor_user_id,
        )
        
        self.audit.log(
            action="wallet.freeze",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="wallet",
            entity_id=wallet.id,
            message=f"Wallet freeze: {amount} {wallet.currency}, reason: {reason}",
        )
        
        return wallet, transaction
    
    def unfreeze(
        self,
        client_id: str,
        amount: Decimal,
        reason: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
        actor_user_id: str | None = None,
    ) -> Tuple[Wallet, WalletTransaction]:
        """
        Разморозить средства.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма разморозки должна быть положительной"
            )
        
        wallet = self._get_wallet(client_id)
        
        if wallet.frozen_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостаточно замороженных средств. Заморожено: {wallet.frozen_balance} {wallet.currency}"
            )
        
        old_frozen = wallet.frozen_balance
        wallet.frozen_balance -= amount
        wallet = self.repository.save(wallet)
        
        transaction = self._add_transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.UNFREEZE.value,
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            description=f"Разморозка средств: {reason}",
            reference_type=reference_type,
            reference_id=reference_id,
            created_by_user_id=actor_user_id,
        )
        
        self.audit.log(
            action="wallet.unfreeze",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="wallet",
            entity_id=wallet.id,
            message=f"Wallet unfreeze: {amount} {wallet.currency}, reason: {reason}",
        )
        
        return wallet, transaction
    
    # ==========================================================
    # ПРОВЕРКА БАЛАНСА
    # ==========================================================
    
    def check_balance(self, client_id: str, amount: Decimal) -> bool:
        """
        Проверить, достаточно ли средств на балансе.
        
        Returns:
            True если достаточно, False если нет
        """
        wallet = self._get_wallet(client_id, create_if_missing=False)
        available_balance = wallet.balance - wallet.frozen_balance
        return available_balance >= amount
    
    def get_available_balance(self, client_id: str) -> Decimal:
        """Получить доступный баланс (без учёта замороженных средств)"""
        wallet = self._get_wallet(client_id, create_if_missing=False)
        return wallet.balance - wallet.frozen_balance