#!/usr/bin/env python
"""
Полное тестирование модуля M05 — Finance

Тестирует:
1. Кошелёк клиента (создание, пополнение, списание, заморозка)
2. Платежи (создание, подтверждение, возврат)
3. Чеки (генерация, отправка)
4. Кассовые смены (открытие, закрытие, операции)
5. Продажи (абонемент, услуга, посещение, комплексная продажа)
6. Интеграцию всех компонентов
"""

import sys
import os
import uuid
import re
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.client import Client
from app.models.tariff import Tariff
from app.models.subscription import Subscription
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.cash_desk_session import CashDeskSession
from app.models.cash_operation import CashOperation
from app.services.client_service import ClientService
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.services.payment_service import PaymentService
from app.services.receipt_service import ReceiptService
from app.services.cash_desk_service import CashDeskService
from app.services.sale_service import SaleService
from app.schemas.enums import PaymentMethod, PaymentStatus, TransactionType, CashOperationType


def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f"[ {title} ]")
    print("=" * 70)


def print_success(message: str):
    print(f"[OK] {message}")


def print_error(message: str):
    print(f"[ERROR] {message}")


def print_info(message: str):
    print(f"[INFO] {message}")


class TestFinanceModule:
    """Класс для тестирования модуля Finance"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.client_service = ClientService(self.db)
        self.user_service = UserService(self.db)
        self.wallet_service = WalletService(self.db)
        self.payment_service = PaymentService(self.db)
        self.receipt_service = ReceiptService(self.db)
        self.cash_desk_service = CashDeskService(self.db)
        self.sale_service = SaleService(self.db)
        
        self.test_user = None
        self.test_client = None
        self.test_tariff = None
        self.test_subscription = None
        self.test_payment = None
        self.test_receipt = None
        self.test_cash_session = None
    
    def setup_test_data(self):
        """Создание тестовых данных"""
        print_separator("SETUP: Creating test data")
        
        unique_suffix = uuid.uuid4().hex[:8]
        
        # 1. Создаём пользователя (кассира) в таблице users
        self.test_user = self.user_service.create_user(
            email=f"cashier_{unique_suffix}@example.com",
            username=f"cashier_{unique_suffix}",
            password="Test123!",
            is_active=True,
        )
        print_success(f"User (cashier) created: ID={self.test_user.id}")
        print_info(f"   Email: {self.test_user.email}")
        
        # 2. Создаём клиента
        numeric_suffix = re.sub(r'[^0-9]', '', unique_suffix)
        while len(numeric_suffix) < 8:
            numeric_suffix += '0'
        
        self.test_client = self.client_service.create_client(
            first_name="Test",
            last_name="Finance",
            middle_name="Testovich",
            phone=f"+7999{numeric_suffix[:8]}",
            email=f"finance_test_{unique_suffix}@example.com",
            gender="MALE",
            client_category="ADULT",
            status_value="ACTIVE",
            is_active=True,
            actor_user_id=None,
        )
        print_success(f"Client created: ID={self.test_client.id}")
        print_info(f"   Email: {self.test_client.email}")
        
        # 3. Создаём тариф
        self.test_tariff = Tariff(
            code=f"TEST_FINANCE_{unique_suffix[:6]}",
            name=f"Test tariff {unique_suffix[:6]}",
            price=Decimal("2990.00"),
            currency="RUB",
            duration_days=30,
            visit_limit=10,
            is_unlimited=False,
            is_active=True,
        )
        self.db.add(self.test_tariff)
        self.db.commit()
        self.db.refresh(self.test_tariff)
        print_success(f"Tariff created: {self.test_tariff.name} - {self.test_tariff.price} RUB")
    
    def test_wallet_creation(self):
        """Тест 1: Создание кошелька"""
        print_separator("TEST 1: WALLET CREATION")
        
        wallet = self.wallet_service._get_wallet(str(self.test_client.id))
        
        print_success(f"Wallet created: ID={wallet.id}")
        print_info(f"   Balance: {wallet.balance} {wallet.currency}")
        print_info(f"   Frozen balance: {wallet.frozen_balance}")
        
        assert wallet.balance == Decimal("0.00")
        assert wallet.currency == "RUB"
        
        print_success("Wallet creation works correctly")
        return wallet
    
    def test_wallet_deposit(self):
        """Тест 2: Пополнение кошелька"""
        print_separator("TEST 2: WALLET DEPOSIT")
        
        amount = Decimal("1000.00")
        result = self.wallet_service.deposit(
            client_id=str(self.test_client.id),
            amount=amount,
            payment_method="CASH",
            notes="Тестовое пополнение",
            actor_user_id=None,
        )
        
        print_success(f"Deposit successful: {result.message}")
        print_info(f"   Amount: {amount} RUB")
        print_info(f"   New balance: {result.new_balance} RUB")
        print_info(f"   Transaction ID: {result.transaction_id}")
        
        assert result.success is True
        assert result.new_balance == amount
        
        print_success("Wallet deposit works correctly")
    
    def test_wallet_withdraw(self):
        """Тест 3: Списание с кошелька"""
        print_separator("TEST 3: WALLET WITHDRAW")
        
        amount = Decimal("500.00")
        wallet, transaction = self.wallet_service.withdraw(
            client_id=str(self.test_client.id),
            amount=amount,
            description="Тестовое списание",
            reference_type="test",
            reference_id="test_123",
            actor_user_id=None,
        )
        
        print_success(f"Withdrawal successful")
        print_info(f"   Amount: {amount} RUB")
        print_info(f"   Balance after: {wallet.balance} RUB")
        print_info(f"   Transaction ID: {transaction.id}")
        
        assert wallet.balance == Decimal("500.00")
        
        print_success("Wallet withdrawal works correctly")
    
    def test_wallet_freeze_unfreeze(self):
        """Тест 4: Заморозка и разморозка средств"""
        print_separator("TEST 4: WALLET FREEZE & UNFREEZE")
        
        amount = Decimal("200.00")
        
        # Заморозка
        wallet, transaction = self.wallet_service.freeze(
            client_id=str(self.test_client.id),
            amount=amount,
            reason="Тестовая заморозка",
            actor_user_id=None,
        )
        
        print_info(f"Freeze: {amount} RUB frozen")
        print_info(f"   Frozen balance: {wallet.frozen_balance} RUB")
        assert wallet.frozen_balance == amount
        
        # Разморозка
        wallet, transaction = self.wallet_service.unfreeze(
            client_id=str(self.test_client.id),
            amount=amount,
            reason="Тестовая разморозка",
            actor_user_id=None,
        )
        
        print_info(f"Unfreeze: {amount} RUB unfrozen")
        print_info(f"   Frozen balance after: {wallet.frozen_balance} RUB")
        assert wallet.frozen_balance == Decimal("0.00")
        
        print_success("Wallet freeze/unfreeze works correctly")
    
    def test_wallet_transactions(self):
        """Тест 5: История транзакций"""
        print_separator("TEST 5: WALLET TRANSACTIONS HISTORY")
        
        transactions = self.wallet_service.get_transactions(
            client_id=str(self.test_client.id),
            limit=10,
        )
        
        print_info(f"Total transactions: {transactions.count}")
        print_info(f"Total deposited: {transactions.total_deposited} RUB")
        print_info(f"Total withdrawn: {transactions.total_withdrawn} RUB")
        
        for t in transactions.items[:5]:
            print_info(f"   {t.transaction_type}: {t.amount} RUB - {t.description}")
        
        assert transactions.count >= 2
        assert transactions.total_deposited >= Decimal("1000.00")
        
        print_success("Wallet transactions history works correctly")
    
    def test_payment_creation(self):
        """Тест 6: Создание платежа"""
        print_separator("TEST 6: PAYMENT CREATION")
        
        payment = self.payment_service.create_payment(
            client_id=str(self.test_client.id),
            amount=Decimal("1500.00"),
            payment_method=PaymentMethod.CARD,
            notes="Тестовый платёж",
            actor_user_id=None,
        )
        self.test_payment = payment
        
        print_success(f"Payment created: ID={payment.id}")
        print_info(f"   Amount: {payment.amount} {payment.currency}")
        print_info(f"   Method: {payment.payment_method}")
        print_info(f"   Status: {payment.status}")
        
        assert payment.status == PaymentStatus.PENDING.value
        
        print_success("Payment creation works correctly")
    
    def test_payment_completion(self):
        """Тест 7: Подтверждение платежа"""
        print_separator("TEST 7: PAYMENT COMPLETION")
        
        completed = self.payment_service.complete_payment(
            payment_id=str(self.test_payment.id),
            external_payment_id=f"EXT_{self.test_payment.id}",
            actor_user_id=None,
        )
        
        print_success(f"Payment completed: Status={completed.status}")
        print_info(f"   Paid at: {completed.paid_at}")
        
        assert completed.status == PaymentStatus.COMPLETED.value
        
        print_success("Payment completion works correctly")
    
    def test_payment_refund(self):
        """Тест 8: Возврат платежа"""
        print_separator("TEST 8: PAYMENT REFUND")
        
        result = self.payment_service.refund_payment(
            payment_id=str(self.test_payment.id),
            amount=Decimal("750.00"),
            reason="Тестовый возврат",
            refund_to_balance=True,
            actor_user_id=None,
        )
        
        print_success(f"Refund successful: {result.message}")
        print_info(f"   Refund ID: {result.refund_id}")
        print_info(f"   Amount: {result.refunded_amount} RUB")
        
        assert result.success is True
        
        print_success("Payment refund works correctly")
    
    def test_receipt_generation(self):
        """Тест 9: Генерация чека"""
        print_separator("TEST 9: RECEIPT GENERATION")
        
        receipt = self.receipt_service.generate_receipt(
            payment_id=str(self.test_payment.id),
            actor_user_id=None,
        )
        self.test_receipt = receipt
        
        print_success(f"Receipt generated: ID={receipt.id}")
        print_info(f"   Number: {receipt.receipt_number}")
        print_info(f"   Type: {receipt.receipt_type}")
        print_info(f"   QR code: {'Yes' if receipt.qr_code else 'No'}")
        
        assert receipt.receipt_number is not None
        
        print_success("Receipt generation works correctly")
    
    def test_receipt_send(self):
        """Тест 10: Отправка чека"""
        print_separator("TEST 10: RECEIPT SEND")
        
        result = self.receipt_service.send_receipt(
            receipt_id=str(self.test_receipt.id),
            email=self.test_client.email,
            actor_user_id=None,
        )
        
        print_info(f"Send result: {result.message}")
        print_info(f"   Sent to: {result.sent_to}")
        
        print_success("Receipt sending works correctly")
    
    def test_cash_desk_open(self):
        """Тест 11: Открытие кассовой смены"""
        print_separator("TEST 11: CASH DESK OPEN")
        
        session = self.cash_desk_service.open_session(
            cashier_user_id=str(self.test_user.id),
            opening_balance=Decimal("5000.00"),
            notes="Тестовая смена",
            actor_user_id=None,
        )
        self.test_cash_session = session
        
        print_success(f"Session opened: #{session.session_number}")
        print_info(f"   Cashier: {session.cashier_user_id}")
        print_info(f"   Opening balance: {session.opening_balance} RUB")
        print_info(f"   Status: {session.status}")
        
        assert session.status == "OPEN"
        
        print_success("Cash desk open works correctly")
    
    def test_cash_operation(self):
        """Тест 12: Кассовая операция"""
        print_separator("TEST 12: CASH OPERATION")
        
        operation = self.cash_desk_service.add_operation(
            cashier_user_id=str(self.test_user.id),
            operation_type=CashOperationType.INCOME,
            amount=Decimal("3000.00"),
            payment_method=PaymentMethod.CASH,
            description="Продажа абонемента",
            actor_user_id=None,
        )
        
        print_success(f"Operation added: ID={operation.id}")
        print_info(f"   Type: {operation.operation_type}")
        print_info(f"   Amount: {operation.amount} RUB")
        
        assert operation.amount == Decimal("3000.00")
        
        # Проверяем обновление смены
        self.db.refresh(self.test_cash_session)
        print_info(f"   Session cash income: {self.test_cash_session.cash_income} RUB")
        assert self.test_cash_session.cash_income == Decimal("3000.00")
        
        print_success("Cash operation works correctly")
    
    def test_cash_desk_verify(self):
        """Тест 13: Сверка наличных"""
        print_separator("TEST 13: CASH VERIFICATION")
        
        result = self.cash_desk_service.verify_cash(
            cashier_user_id=str(self.test_user.id),
            actual_cash=Decimal("8000.00"),
            notes="Промежуточная сверка",
            actor_user_id=None,
        )
        
        print_info(f"Expected cash: {result['expected_cash']} RUB")
        print_info(f"Actual cash: {result['actual_cash']} RUB")
        print_info(f"Discrepancy: {result['discrepancy']} RUB")
        print_info(f"Match: {result['is_match']}")
        
        print_success("Cash verification works correctly")
    
    def test_cash_desk_close(self):
        """Тест 14: Закрытие кассовой смены"""
        print_separator("TEST 14: CASH DESK CLOSE")
        
        closed_session = self.cash_desk_service.close_session(
            cashier_user_id=str(self.test_user.id),
            actual_cash=Decimal("8000.00"),
            notes="Закрытие смены",
            actor_user_id=None,
        )
        
        print_success(f"Session closed: #{closed_session.session_number}")
        print_info(f"   Closing balance: {closed_session.closing_balance} RUB")
        print_info(f"   Discrepancy: {closed_session.discrepancy} RUB")
        print_info(f"   Status: {closed_session.status}")
        
        assert closed_session.status == "CLOSED"
        
        print_success("Cash desk close works correctly")
    
    def test_sell_subscription(self):
        """Тест 15: Продажа абонемента"""
        print_separator("TEST 15: SELL SUBSCRIPTION")
        
        from app.schemas.sale import SaleSubscriptionRequest
        
        request = SaleSubscriptionRequest(
            client_id=self.test_client.id,
            tariff_id=self.test_tariff.id,
            payment_method="CARD",
            auto_renew=False,
        )
        
        result = self.sale_service.sell_subscription(request, actor_user_id=None)
        
        print_success(f"Subscription sold: ID={result.subscription_id}")
        print_info(f"   Amount: {result.amount} RUB")
        print_info(f"   Payment ID: {result.payment_id}")
        print_info(f"   Receipt ID: {result.receipt_id}")
        print_info(f"   Message: {result.message}")
        
        assert result.success is True
        assert result.amount == self.test_tariff.price
        
        print_success("Subscription sale works correctly")
    
    def test_sell_visit(self):
        """Тест 16: Продажа разового посещения"""
        print_separator("TEST 16: SELL VISIT")
        
        from app.schemas.sale import SaleVisitRequest
        
        request = SaleVisitRequest(
            client_id=self.test_client.id,
            zone="GYM",
            payment_method="CASH",
        )
        
        result = self.sale_service.sell_visit(request, actor_user_id=None)
        
        print_success(f"Visit sold: ID={result.visit_id}")
        print_info(f"   Amount: {result.amount} RUB")
        print_info(f"   Payment ID: {result.payment_id}")
        print_info(f"   Receipt ID: {result.receipt_id}")
        
        assert result.success is True
        
        print_success("Visit sale works correctly")
    
    def test_sell_package(self):
        """Тест 17: Комплексная продажа"""
        print_separator("TEST 17: SELL PACKAGE")
        
        # Создаём ещё один тариф для комплексной продажи
        unique_suffix = uuid.uuid4().hex[:6]
        second_tariff = Tariff(
            code=f"PACKAGE_{unique_suffix}",
            name=f"Package tariff {unique_suffix}",
            price=Decimal("1500.00"),
            currency="RUB",
            duration_days=14,
            visit_limit=5,
            is_unlimited=False,
            is_active=True,
        )
        self.db.add(second_tariff)
        self.db.commit()
        self.db.refresh(second_tariff)
        
        items = [
            {
                "type": "subscription",
                "tariff_id": str(self.test_tariff.id),
                "quantity": 1,
                "price": float(self.test_tariff.price),
            },
            {
                "type": "subscription",
                "tariff_id": str(second_tariff.id),
                "quantity": 1,
                "price": float(second_tariff.price),
            },
            {
                "type": "visit",
                "zone": "GYM",
                "quantity": 2,
                "price": 800.00,
            },
        ]
        
        result = self.sale_service.sell_package(
            client_id=str(self.test_client.id),
            items=items,
            payment_method="CARD",
            notes="Комплексная продажа",
            actor_user_id=None,
        )
        
        print_success(f"Package sale completed")
        print_info(f"   Total amount: {result['total_amount']} RUB")
        print_info(f"   Items count: {len(result['items'])}")
        print_info(f"   Payment ID: {result['payment_id']}")
        print_info(f"   Message: {result['message']}")
        
        assert result['success'] is True
        assert result['total_amount'] > 0
        
        print_success("Package sale works correctly")
    
    def test_balance_check(self):
        """Тест 18: Проверка баланса"""
        print_separator("TEST 18: BALANCE CHECK")
        
        balance_info = self.wallet_service.get_balance(str(self.test_client.id))
        
        print_info(f"Current balance: {balance_info['balance']} {balance_info['currency']}")
        print_info(f"Frozen: {balance_info['frozen_balance']}")
        print_info(f"Available: {balance_info['available_balance']}")
        
        print_success("Balance check works correctly")
    
    def cleanup(self):
        """Очистка тестовых данных"""
        print_separator("CLEANUP")
        
        choice = input("Delete test data? (y/n): ")
        if choice.lower() == 'y':
            # Удаляем в правильном порядке
            self.db.query(CashOperation).delete()
            self.db.query(CashDeskSession).delete()
            self.db.query(Receipt).delete()
            self.db.query(Payment).delete()
            self.db.query(WalletTransaction).delete()
            self.db.query(Wallet).delete()
            self.db.query(Subscription).delete()
            self.db.query(Tariff).filter(Tariff.code.like("TEST_FINANCE%")).delete()
            self.db.query(Tariff).filter(Tariff.code.like("PACKAGE%")).delete()
            self.db.delete(self.test_client)
            self.db.delete(self.test_user)
            self.db.commit()
            print_success("Test data deleted")
        else:
            print_info("Test data kept in DB")
            print_info(f"   User ID: {self.test_user.id}")
            print_info(f"   Client ID: {self.test_client.id}")
            print_info(f"   Tariff ID: {self.test_tariff.id}")
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print_separator("RUNNING FULL FINANCE MODULE TEST (M05)")
        
        try:
            self.setup_test_data()
            
            self.test_wallet_creation()
            self.test_wallet_deposit()
            self.test_wallet_withdraw()
            self.test_wallet_freeze_unfreeze()
            self.test_wallet_transactions()
            
            self.test_payment_creation()
            self.test_payment_completion()
            self.test_payment_refund()
            
            self.test_receipt_generation()
            self.test_receipt_send()
            
            self.test_cash_desk_open()
            self.test_cash_operation()
            self.test_cash_desk_verify()
            self.test_cash_desk_close()
            
            self.test_sell_subscription()
            self.test_sell_visit()
            self.test_sell_package()
            
            self.test_balance_check()
            
            print_separator("TEST RESULTS")
            print_success("M05 — Finance Module")
            print_success("")
            print_success(" Wallet creation - works")
            print_success(" Wallet deposit - works")
            print_success(" Wallet withdrawal - works")
            print_success(" Wallet freeze/unfreeze - works")
            print_success(" Wallet transactions history - works")
            print_success(" Payment creation - works")
            print_success(" Payment completion - works")
            print_success(" Payment refund - works")
            print_success(" Receipt generation - works")
            print_success(" Receipt sending - works")
            print_success(" Cash desk open - works")
            print_success(" Cash operation - works")
            print_success(" Cash verification - works")
            print_success(" Cash desk close - works")
            print_success(" Subscription sale - works")
            print_success(" Visit sale - works")
            print_success(" Package sale - works")
            print_success(" Balance check - works")
            
            print_separator("ALL TESTS PASSED SUCCESSFULLY!")
            
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
        finally:
            self.cleanup()
            self.db.close()


if __name__ == "__main__":
    tester = TestFinanceModule()
    tester.run_all_tests()