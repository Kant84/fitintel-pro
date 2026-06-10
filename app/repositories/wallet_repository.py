# app/repositories/wallet_repository.py

from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction


class WalletRepository:
    """Репозиторий для работы с кошельками"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_client_id(self, client_id: str) -> Optional[Wallet]:
        """Получить кошелёк по ID клиента"""
        return self.db.query(Wallet).filter(Wallet.client_id == client_id).first()
    
    def get_by_id(self, wallet_id: str) -> Optional[Wallet]:
        """Получить кошелёк по ID"""
        return self.db.query(Wallet).filter(Wallet.id == wallet_id).first()
    
    def create(self, client_id: str, currency: str = "RUB") -> Wallet:
        """Создать кошелёк для клиента"""
        wallet = Wallet(
            client_id=client_id,
            balance=Decimal("0.00"),
            currency=currency,
            frozen_balance=Decimal("0.00"),
        )
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)
        return wallet
    
    def save(self, wallet: Wallet) -> Wallet:
        """Сохранить изменения"""
        self.db.commit()
        self.db.refresh(wallet)
        return wallet
    
    def add_transaction(self, transaction: WalletTransaction) -> WalletTransaction:
        """Добавить транзакцию"""
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction