# app/services/payment_service.py

from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
import hashlib
import hmac
import json
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.client import Client
from app.models.wallet import Wallet
from app.repositories.payment_repository import PaymentRepository
from app.repositories.wallet_repository import WalletRepository
from app.services.audit_service import AuditService
from app.services.wallet_service import WalletService
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentListResponse,
    PaymentOnlineResponse,
    PaymentRefundRequest,
    PaymentRefundResponse,
    PaymentWebhookRequest,
)
from app.schemas.enums import PaymentMethod, PaymentStatus, PaymentSystem


class PaymentService:
    """
    Сервис для управления платежами.
    
    Включает:
    - Создание платежей (наличные, карта, онлайн, СБП)
    - Подтверждение платежей
    - Возвраты
    - Интеграцию с платёжными системами (заглушки)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = PaymentRepository(db)
        self.wallet_repository = WalletRepository(db)
        self.wallet_service = WalletService(db)
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
    
    def _generate_payment_number(self) -> str:
        """Сгенерировать уникальный номер платежа"""
        import uuid
        return f"PAY-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    def _build_response(self, payment: Payment) -> dict:
        """Построить ответ платежа (полные данные как в чеке)"""
        # Получаем данные клиента (раздельные поля ФИО)
        client_first_name = None
        client_last_name = None
        client_middle_name = None
        client_full_name = None
        client_phone = None
        client_email = None
        if payment.client:
            client_first_name = payment.client.first_name
            client_last_name = payment.client.last_name
            client_middle_name = payment.client.middle_name
            parts = [p for p in [client_last_name, client_first_name, client_middle_name] if p]
            client_full_name = " ".join(parts)
            client_phone = payment.client.phone
            client_email = payment.client.email
        
        # Получаем номер чека
        receipt_number = None
        if payment.receipt:
            receipt_number = payment.receipt.receipt_number
        
        # Получаем название абонемента (если есть)
        subscription_name = None
        purpose = payment.notes
        if hasattr(payment, 'subscription') and payment.subscription:
            subscription_name = payment.subscription.name
            purpose = f"Оплата абонемента: {payment.subscription.name}"
        
        # Вид платежа (Наличные/Безналичные)
        payment_type = "Наличные"
        if payment.payment_method in ["CARD", "SBP", "ONLINE", "TRANSFER"]:
            payment_type = "Безналичные"
        
        # Название банка/платёжной системы (для безналичных)
        bank_name = payment.payment_system
        if not bank_name:
            if payment.payment_method == "SBP":
                bank_name = "Система быстрых платежей (СБП)"
            elif payment.payment_method == "CARD":
                bank_name = "Банковская карта (не указан банк)"
            elif payment.payment_method == "CASH":
                bank_name = None  # Для наличных банк не нужен
            else:
                bank_name = "Не указан"
        
        return {
            "id": payment.id,
            "client_id": payment.client_id,
            # Данные клиента (как в чеке)
            "client_first_name": client_first_name,
            "client_last_name": client_last_name,
            "client_middle_name": client_middle_name,
            "client_full_name": client_full_name,
            "client_phone": client_phone,
            "client_email": client_email,
            # Данные платежа
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_type": payment_type,
            "bank_name": bank_name,
            "payment_direction": payment.payment_direction,
            "payment_category": payment.payment_category,
            "status": payment.status,
            "external_payment_id": payment.external_payment_id,
            "paid_at": payment.paid_at,
            # Данные чека
            "receipt_number": receipt_number,
            "purpose": purpose,
            "subscription_name": subscription_name,
            # Служебные
            "created_by_user_id": payment.created_by_user_id,
            "notes": payment.notes,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }
    
    # ==========================================================
    # ОСНОВНЫЕ ОПЕРАЦИИ
    # ==========================================================
    
    def create_payment(
        self,
        client_id: str,
        amount: Decimal,
        payment_method: PaymentMethod,
        payment_system: PaymentSystem | None = None,
        notes: str | None = None,
        return_url: str | None = None,
        webhook_url: str | None = None,
        payment_direction: str = "INCOME",
        payment_category: str = "SUBSCRIPTION",
        actor_user_id: str | None = None,
    ) -> Payment:
        """
        Создать платёж.
        
        Args:
            client_id: ID клиента
            amount: Сумма
            payment_method: Способ оплаты (CASH, CARD, ONLINE, BALANCE, SBP)
            payment_system: Платёжная система (для онлайн-платежей)
            notes: Заметки
            return_url: URL для возврата (для онлайн)
            webhook_url: URL для уведомлений
            actor_user_id: Кто создал
        
        Returns:
            Созданный платёж
        """
        # Проверяем клиента только если указан
        client = None
        if client_id:
            client = self._get_client(client_id)
        
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма платежа должна быть положительной"
            )
        
        # Проверка баланса при оплате с баланса
        if payment_method == PaymentMethod.BALANCE:
            if not self.wallet_service.check_balance(client_id, amount):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Недостаточно средств на балансе"
                )
        
        payment = Payment(
            client_id=client_id,
            amount=amount,
            currency="RUB",
            payment_method=payment_method.value,
            status=PaymentStatus.PENDING.value,
            payment_system=payment_system.value if payment_system else None,
            payment_direction=payment_direction,
            payment_category=payment_category,
            notes=notes,
            created_by_user_id=actor_user_id,
        )
        
        created_payment = self.repository.add(payment)
        
        client_info = client.email if client else "внутренний платёж"
        self.audit.log(
            action="payment.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=created_payment.id,
            message=f"Payment created for {client_info}: {amount} RUB",
            after_data={
                "client_id": client_id,
                "amount": str(amount),
                "payment_method": payment_method.value,
                "payment_system": payment_system.value if payment_system else None,
                "payment_direction": payment_direction,
                "payment_category": payment_category,
            },
        )
        
        return created_payment
    
    def complete_payment(
        self,
        payment_id: str,
        external_payment_id: str | None = None,
        transaction_data: dict | None = None,
        actor_user_id: str | None = None,
    ) -> Payment:
        """
        Подтвердить платёж (списать средства).
        
        Args:
            payment_id: ID платежа
            external_payment_id: ID во внешней системе
            transaction_data: Данные транзакции
            actor_user_id: Кто подтвердил
        
        Returns:
            Подтверждённый платёж
        """
        payment = self.repository.get_by_id(payment_id)
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Платёж не найден"
            )
        
        if payment.status != PaymentStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно подтвердить платёж в статусе {payment.status}"
            )
        
        client = self._get_client(payment.client_id)
        
        # Обработка в зависимости от способа оплаты
        if payment.payment_method == PaymentMethod.BALANCE.value:
            # Списание с баланса
            self.wallet_service.withdraw(
                client_id=payment.client_id,
                amount=payment.amount,
                description=f"Оплата {payment.id}",
                reference_type="payment",
                reference_id=payment.id,
                actor_user_id=actor_user_id,
            )
        
        # Обновляем статус
        payment.status = PaymentStatus.COMPLETED.value
        payment.paid_at = datetime.now()
        if external_payment_id:
            payment.external_payment_id = external_payment_id
        
        updated_payment = self.repository.save(payment)
        
        self.audit.log(
            action="payment.completed",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=payment.id,
            message=f"Payment completed for client {client.email}: {payment.amount} RUB",
            after_data={
                "payment_id": payment_id,
                "external_payment_id": external_payment_id,
            },
        )
        
        return updated_payment
    
    def fail_payment(
        self,
        payment_id: str,
        reason: str,
        actor_user_id: str | None = None,
    ) -> Payment:
        """Отметить платёж как неуспешный"""
        payment = self.repository.get_by_id(payment_id)
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Платёж не найден"
            )
        
        if payment.status != PaymentStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно отменить платёж в статусе {payment.status}"
            )
        
        payment.status = PaymentStatus.FAILED.value
        payment.notes = f"{payment.notes or ''}\nОшибка: {reason}".strip()
        
        updated_payment = self.repository.save(payment)
        
        self.audit.log(
            action="payment.failed",
            status="failed",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=payment.id,
            message=f"Payment failed: {reason}",
        )
        
        return updated_payment
    
    # ==========================================================
    # ВОЗВРАТЫ
    # ==========================================================
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Decimal | None = None,
        reason: str = "Возврат",
        refund_to_balance: bool = False,
        actor_user_id: str | None = None,
    ) -> PaymentRefundResponse:
        """
        Возврат платежа.
        
        Args:
            payment_id: ID платежа
            amount: Сумма возврата (если None — полный возврат)
            reason: Причина возврата
            refund_to_balance: Вернуть на баланс кошелька
            actor_user_id: Кто выполняет возврат
        
        Returns:
            Результат возврата
        """
        payment = self.repository.get_by_id(payment_id)
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Платёж не найден"
            )
        
        if payment.status != PaymentStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно вернуть платёж в статусе {payment.status}"
            )
        
        refund_amount = amount or payment.amount
        
        if refund_amount > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма возврата не может превышать сумму платежа"
            )
        
        # Создаём платёж возврата
        refund_payment = Payment(
            client_id=payment.client_id,
            amount=refund_amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            status=PaymentStatus.COMPLETED.value,
            notes=f"Возврат платежа {payment.id}. Причина: {reason}",
            created_by_user_id=actor_user_id,
            paid_at=datetime.now(),
        )
        self.db.add(refund_payment)
        
        # Если возврат на баланс
        if refund_to_balance:
            self.wallet_service.deposit(
                client_id=payment.client_id,
                amount=refund_amount,
                payment_method="REFUND",
                notes=f"Возврат средств по платежу {payment.id}",
                reference_type="refund",
                reference_id=refund_payment.id,
                actor_user_id=actor_user_id,
            )
        
        # Обновляем оригинальный платёж
        if refund_amount == payment.amount:
            payment.status = PaymentStatus.REFUNDED.value
        else:
            payment.status = PaymentStatus.REFUNDED.value
            payment.notes = f"{payment.notes or ''}\nЧастичный возврат: {refund_amount} RUB".strip()
        
        self.db.commit()
        
        # Создаём чек возврата (после commit, ID сгенерирован)
        from app.models.receipt import Receipt
        import uuid
        receipt = Receipt(
            payment_id=refund_payment.id,
            receipt_number=f"REF-{uuid.uuid4().hex[:8].upper()}",
            receipt_type="REFUND",
            fiscal_sign=None,
            fiscal_document_number=None,
            fiscal_document_date=None,
            ofd_url=None,
            qr_code=None,
        )
        self.db.add(receipt)
        self.db.commit()
        
        self.audit.log(
            action="payment.refunded",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=payment.id,
            message=f"Payment refunded: {refund_amount} RUB, reason: {reason}",
            after_data={
                "original_payment_id": payment_id,
                "refund_payment_id": refund_payment.id,
                "amount": str(refund_amount),
                "refund_to_balance": refund_to_balance,
            },
        )
        
        return PaymentRefundResponse(
            success=True,
            refund_id=refund_payment.id,
            refunded_amount=refund_amount,
            message=f"Возврат на сумму {refund_amount} RUB выполнен успешно",
        )
    
    # ==========================================================
    # ОНЛАЙН-ПЛАТЕЖИ (ЭКВАЙРИНГ)
    # ==========================================================
    
    def create_online_payment(
        self,
        client_id: str,
        amount: Decimal,
        payment_method: PaymentMethod,
        return_url: str | None = None,
        webhook_url: str | None = None,
        actor_user_id: str | None = None,
    ) -> PaymentOnlineResponse:
        """
        Создать онлайн-платёж (через эквайринг).
        
        Поддерживает:
        - Банковские карты (CARD)
        - СБП (SBP)
        """
        # Создаём платёж
        payment = self.create_payment(
            client_id=client_id,
            amount=amount,
            payment_method=payment_method,
            payment_system=PaymentSystem.T_BANK,  # по умолчанию Т-Банк
            actor_user_id=actor_user_id,
        )
        
        # Здесь будет реальная интеграция с API эквайринга
        # Пока заглушка
        payment_url = f"https://payment.example.com/pay/{payment.id}"
        
        # Для СБП — генерируем QR-код
        sbp_data = None
        if payment_method == PaymentMethod.SBP:
            sbp_data = self._generate_sbp_qr(str(payment.id), amount)
        
        return PaymentOnlineResponse(
            payment_id=payment.id,
            payment_url=payment_url,
            requires_redirect=payment_method != PaymentMethod.SBP,
            transaction_id=f"TXN_{payment.id}",
            sbp_qr_code=sbp_data.get("qr_code_base64") if sbp_data else None,
            sbp_deeplink=sbp_data.get("deeplink") if sbp_data else None,
        )
    
    def _generate_sbp_qr(self, payment_id: str, amount: Decimal) -> dict:
        """
        Генерация QR-кода СБП.
        
        В реальности здесь будет запрос к API банка/агрегатора.
        """
        # Заглушка для разработки
        return {
            "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
            "deeplink": f"https://qr.nspk.ru/{payment_id}",
        }
    
    def handle_webhook(
        self,
        payment_system: str,
        raw_data: dict,
        signature: str | None = None,
    ) -> dict:
        """
        Обработка вебхука от платёжной системы.
        
        Args:
            payment_system: Платёжная система (tbank, sberbank, cloudpayments)
            raw_data: Сырые данные от платёжной системы
            signature: Подпись для проверки
        
        Returns:
            Результат обработки
        """
        # Проверка подписи (если есть)
        if signature and not self._verify_webhook_signature(payment_system, raw_data, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Извлекаем данные
        external_payment_id = raw_data.get("payment_id") or raw_data.get("order_id")
        status = raw_data.get("status")
        
        if not external_payment_id:
            return {"status": "error", "message": "No payment_id in webhook"}
        
        # Ищем платёж
        payment = self.repository.get_by_external_id(external_payment_id)
        if not payment:
            # Пробуем найти по ID
            payment = self.repository.get_by_id(external_payment_id)
        
        if not payment:
            return {"status": "error", "message": "Payment not found"}
        
        # Обновляем статус
        if status in ["succeeded", "completed", "paid"]:
            self.complete_payment(
                payment_id=str(payment.id),
                external_payment_id=external_payment_id,
                transaction_data=raw_data,
            )
        elif status in ["failed", "cancelled"]:
            self.fail_payment(
                payment_id=str(payment.id),
                reason=raw_data.get("failure_reason", "Payment failed"),
            )
        
        return {"status": "ok"}
    
    def _verify_webhook_signature(self, payment_system: str, data: dict, signature: str) -> bool:
        """Проверить подпись вебхука"""
        # Заглушка — в реальности проверяем подпись
        return True
    
    # ==========================================================
    # ПОЛУЧЕНИЕ ДАННЫХ
    # ==========================================================
    
    def get_payment(self, payment_id: str) -> Payment:
        """Получить платёж по ID"""
        payment = self.repository.get_by_id(payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Платёж не найден"
            )
        return payment
    
    def get_client_payments(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
        status_filter: str | None = None,
    ) -> PaymentListResponse:
        """Получить платежи клиента"""
        client = self._get_client(client_id)
        
        payments = self.repository.list_by_client(
            client_id=client_id,
            limit=limit,
            offset=offset,
            status=status_filter,
        )
        
        total_amount = sum(p.amount for p in payments)
        
        return PaymentListResponse(
            items=[self._build_response(p) for p in payments],
            count=len(payments),
            total_amount=total_amount,
        )