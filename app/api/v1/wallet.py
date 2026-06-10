# app/api/v1/wallet.py

from uuid import UUID
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.wallet import (
    WalletResponse,
    WalletTransactionListResponse,
    WalletDepositRequest,
    WalletDepositResponse,
)
from app.schemas.enums import TransactionType
from app.services.wallet_service import WalletService


router = APIRouter(prefix="/wallet", tags=["Wallet"])


# ==========================================================
# ДЛЯ КЛИЕНТА (self-service)
# ==========================================================

@router.get("/me", response_model=WalletResponse)
def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить свой кошелёк (для клиента).
    
    Доступно в личном кабинете клиента.
    """
    service = WalletService(db)
    wallet = service.get_wallet(str(current_user.id))
    
    return {
        "id": wallet.id,
        "client_id": wallet.client_id,
        "balance": wallet.balance,
        "currency": wallet.currency,
        "frozen_balance": wallet.frozen_balance,
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at,
    }


@router.get("/me/balance")
def get_my_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить свой баланс"""
    service = WalletService(db)
    return service.get_balance(str(current_user.id))


@router.get("/me/transactions", response_model=WalletTransactionListResponse)
def get_my_transactions(
    transaction_type: TransactionType | None = Query(default=None, description="Тип транзакции"),
    start_date: datetime | None = Query(default=None, description="Дата начала"),
    end_date: datetime | None = Query(default=None, description="Дата окончания"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить историю своих транзакций"""
    service = WalletService(db)
    return service.get_transactions(
        client_id=str(current_user.id),
        transaction_type=transaction_type.value if transaction_type else None,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


# ==========================================================
# ДЛЯ АДМИНИСТРАТОРОВ
# ==========================================================

@router.get("/client/{client_id}", response_model=WalletResponse)
def get_client_wallet(
    client_id: UUID,
    current_user: User = Depends(require_permission("wallet.read")),
    db: Session = Depends(get_db),
):
    """Получить кошелёк клиента (администратор)"""
    service = WalletService(db)
    wallet = service.get_wallet(str(client_id))
    
    return {
        "id": wallet.id,
        "client_id": wallet.client_id,
        "balance": wallet.balance,
        "currency": wallet.currency,
        "frozen_balance": wallet.frozen_balance,
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at,
    }


@router.get("/client/{client_id}/balance")
def get_client_balance(
    client_id: UUID,
    current_user: User = Depends(require_permission("wallet.read")),
    db: Session = Depends(get_db),
):
    """Получить баланс клиента (администратор)"""
    service = WalletService(db)
    return service.get_balance(str(client_id))


@router.get("/client/{client_id}/transactions", response_model=WalletTransactionListResponse)
def get_client_transactions(
    client_id: UUID,
    transaction_type: TransactionType | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("wallet.read")),
    db: Session = Depends(get_db),
):
    """Получить историю транзакций клиента (администратор)"""
    service = WalletService(db)
    return service.get_transactions(
        client_id=str(client_id),
        transaction_type=transaction_type.value if transaction_type else None,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.post("/client/{client_id}/deposit", response_model=WalletDepositResponse)
def deposit_to_client(
    client_id: UUID,
    payload: WalletDepositRequest,
    current_user: User = Depends(require_permission("wallet.deposit")),
    db: Session = Depends(get_db),
):
    """Пополнить баланс клиента (администратор)"""
    service = WalletService(db)
    return service.deposit(
        client_id=str(client_id),
        amount=payload.amount,
        payment_method=payload.payment_method,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )