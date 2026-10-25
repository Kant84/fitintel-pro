# app/services/payment_service.py

from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import base64
import hashlib
import hmac
import json
import os
import re
from fastapi import HTTPException, status
from sqlalchemy import text
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
    
    def _create_accounting_entry(self, payment, kind="sale"):
        """E33: автопроводка двойной записи из платежа (таблица accounting_entries).
        kind="sale" — оплата, kind="refund" — сторно возврата.
        Наличные → счёт 50, безнал → 57; приход → Кт 90.1, расход → Дт 91.2."""
        TABLE = "accounting_entries"
        try:
            from sqlalchemy import text
            from datetime import datetime as _dt
            method = (payment.payment_method or "").upper()
            direction = (payment.payment_direction or "INCOMING").upper()
            cash_acct = "50" if method == "CASH" else "57"
            if kind == "refund":
                d, c = "90.1", cash_acct
                desc = "Сторно возврата: %s" % (payment.notes or payment.id)
            elif direction in ("OUTGOING", "EXPENSE"):
                d, c = "91.2", cash_acct
                desc = "Расход (%s): %s" % (method, payment.notes or payment.id)
            else:
                d, c = cash_acct, "90.1"
                desc = "Оплата (%s): %s" % (method, payment.notes or payment.id)
            cols = {r[0] for r in self.db.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t"), {"t": TABLE}).fetchall()}
            if not cols:
                return
            # id НЕ передаём — генерирует БД (gen_random_uuid()).
            # created_at НЕ передаём — default now().
            data = {"entry_date": _dt.now().date(),
                    "debit_account": d,
                    "credit_account": c,
                    "amount": float(payment.amount),
                    "description": desc[:500],
                    "source": "payment",
                    "is_closing": False}
            data = {k: v for k, v in data.items() if k in cols and v is not None}
            self.db.execute(text(
                "INSERT INTO %s (%s) VALUES (%s)"
                % (TABLE, ", ".join(data), ", ".join(":" + k for k in data))), data)
            self.db.commit()
        except Exception:
            self.db.rollback()  # проводка — не должна ломать платёж
            import traceback
            traceback.print_exc()  # ошибка будет видна в логах api

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
        self._create_accounting_entry(updated_payment, kind="sale")
        
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
        Возврат платежа (E33): полный/частичный; сначала возвратный чек на ККТ.

        Баланс смены:
        - полный возврат: оригинал → REFUNDED (исключается), платёж-возврат
          с direction=REFUND (тоже исключается) → нулевой эффект;
        - частичный: оригинал остаётся COMPLETED (+полная сумма), платёж-возврат
          с direction=OUTGOING (−сумма возврата) → баланс уменьшается корректно.
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

        is_full = refund_amount >= payment.amount

        # 1. СНАЧАЛА возвратный чек на кассу (54-ФЗ): при закрытой смене
        #    _fiscalize бросит 400 — возврат НЕ оформится, деньги не тронуты
        from app.api.v1.fiscal import _fiscalize, _get_settings
        _fiscalize(self.db, _get_settings(self.db)["driver"], "refund",
                   float(refund_amount),
                   payload={"items": [{"name": payment.payment_category or "Возврат",
                                       "price": float(refund_amount), "quantity": 1}],
                            "refund_of": str(payment.id)})

        # 2. Платёж возврата
        refund_payment = Payment(
            client_id=payment.client_id,
            amount=refund_amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            payment_direction="REFUND" if is_full else "OUTGOING",
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

        # 3. Оригинал: полный возврат → REFUNDED; частичный → остаётся COMPLETED
        if is_full:
            payment.status = PaymentStatus.REFUNDED.value
        payment.notes = (payment.notes or "") + \
            f"\nВозврат {refund_amount} RUB: {reason}".strip()

        self.db.commit()

        # Чек возврата (внутренний номер; фискальный уже пробит на ККТ шагом 1)
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
        self._create_accounting_entry(refund_payment, kind="refund")

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
    
    @staticmethod
    def _webhook_secret_name(payment_system: str) -> str:
        """Вернуть имя provider-specific секрета без небезопасного default."""
        provider = re.sub(r"[^A-Z0-9_]", "_", payment_system.upper())
        return f"PAYMENT_WEBHOOK_SECRET_{provider}"

    def _verify_webhook_signature(
        self,
        payment_system: str,
        raw_body: bytes,
        signature: str | None,
    ) -> None:
        """Проверить HMAC-SHA256 исходных байтов запроса."""
        secret_name = self._webhook_secret_name(payment_system)
        secret = os.getenv(secret_name, "")
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Webhook secret is not configured: {secret_name}",
            )
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook signature is required",
            )

        digest = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).digest()
        expected_hex = digest.hex()
        expected_base64 = base64.b64encode(digest).decode("ascii")
        received = signature.strip()
        if received.lower().startswith("sha256="):
            received = received[7:]

        valid = (
            hmac.compare_digest(received.lower(), expected_hex)
            or hmac.compare_digest(received, expected_base64)
        )
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    @staticmethod
    def _ensure_webhook_events(db: Session) -> None:
        """Создать журнал антидубля без сохранения платёжного payload."""
        db.execute(text(
            "CREATE TABLE IF NOT EXISTS payment_webhook_events ("
            "id VARCHAR(36) PRIMARY KEY, "
            "event_key VARCHAR(512) NOT NULL UNIQUE, "
            "payment_system VARCHAR(50) NOT NULL, "
            "external_payment_id VARCHAR(255), "
            "event_status VARCHAR(50), "
            "payload_hash VARCHAR(64) NOT NULL, "
            "created_at TIMESTAMP NOT NULL)"
        ))
        db.commit()

    @staticmethod
    def _webhook_event_key(
        payment_system: str,
        raw_data: dict,
        external_payment_id: str,
        payload_hash: str,
    ) -> str:
        event_id = raw_data.get("event_id") or raw_data.get("notification_id")
        if event_id:
            return f"{payment_system}:event:{event_id}"
        event_status = str(raw_data.get("status") or "unknown").lower()
        return (
            f"{payment_system}:{external_payment_id}:"
            f"{event_status}:{payload_hash}"
        )

    def handle_webhook(
        self,
        payment_system: str,
        raw_body: bytes,
        signature: str | None = None,
    ) -> dict:
        """Проверить подпись и применить платёжное событие не более одного раза."""
        self._verify_webhook_signature(
            payment_system=payment_system,
            raw_body=raw_body,
            signature=signature,
        )

        try:
            raw_data = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook JSON",
            ) from exc
        if not isinstance(raw_data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook JSON must be an object",
            )

        external_payment_id = (
            raw_data.get("payment_id") or raw_data.get("order_id")
        )
        payment_status = str(raw_data.get("status") or "").lower()
        if not external_payment_id:
            return {"status": "error", "message": "No payment_id in webhook"}

        payload_hash = hashlib.sha256(raw_body).hexdigest()
        event_key = self._webhook_event_key(
            payment_system=payment_system,
            raw_data=raw_data,
            external_payment_id=str(external_payment_id),
            payload_hash=payload_hash,
        )
        self._ensure_webhook_events(self.db)
        duplicate = self.db.execute(
            text(
                "SELECT 1 FROM payment_webhook_events "
                "WHERE event_key = :event_key"
            ),
            {"event_key": event_key},
        ).first()
        if duplicate:
            return {"status": "ok", "duplicate": True}

        payment = self.repository.get_by_external_id(external_payment_id)
        if not payment:
            payment = self.repository.get_by_id(external_payment_id)
        if not payment:
            return {"status": "error", "message": "Payment not found"}

        succeeded = payment_status in ("succeeded", "completed", "paid")
        canceled = payment_status in ("failed", "cancelled", "canceled")
        refunded = payment_status in ("refunded", "refund")
        already_applied = False

        if succeeded:
            if payment.status == PaymentStatus.COMPLETED.value:
                already_applied = True
            else:
                self.complete_payment(
                    payment_id=str(payment.id),
                    external_payment_id=str(external_payment_id),
                    transaction_data=raw_data,
                )
        elif canceled:
            if payment.status == PaymentStatus.FAILED.value:
                already_applied = True
            else:
                self.fail_payment(
                    payment_id=str(payment.id),
                    reason=raw_data.get(
                        "failure_reason",
                        "Payment failed or canceled",
                    ),
                )
        elif refunded:
            if payment.status == PaymentStatus.REFUNDED.value:
                already_applied = True
            else:
                amount = raw_data.get("amount")
                self.refund_payment(
                    payment_id=str(payment.id),
                    amount=(
                        Decimal(str(amount))
                        if amount is not None
                        else None
                    ),
                    reason=raw_data.get(
                        "refund_reason",
                        "Возврат подтверждён платёжной системой",
                    ),
                )

        self.db.execute(
            text(
                "INSERT INTO payment_webhook_events "
                "(id, event_key, payment_system, external_payment_id, "
                "event_status, payload_hash, created_at) "
                "VALUES (:id, :event_key, :payment_system, "
                ":external_payment_id, :event_status, :payload_hash, "
                ":created_at)"
            ),
            {
                "id": str(uuid4()),
                "event_key": event_key,
                "payment_system": payment_system,
                "external_payment_id": str(external_payment_id),
                "event_status": payment_status,
                "payload_hash": payload_hash,
                "created_at": datetime.now(),
            },
        )
        self.db.commit()
        return {"status": "ok", "duplicate": already_applied}

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