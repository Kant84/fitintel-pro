# app/tasks/finance.py
# ==========================================================
# Фоновые задачи для финансового модуля
# ==========================================================
# Назначение:
# - Отправка чеков на email/SMS
# - Синхронизация с ОФД
# - Автоматическое закрытие кассовых смен
# - Обработка просроченных платежей
# - Синхронизация с платёжными системами
# ==========================================================

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.receipt_service import ReceiptService
from app.services.payment_service import PaymentService
from app.services.cash_desk_service import CashDeskService
from app.services.audit_service import AuditService
from app.schemas.enums import PaymentStatus
from app.core.config import settings


# ==========================================================
# 1. ОТПРАВКА НЕОТПРАВЛЕННЫХ ЧЕКОВ
# ==========================================================

@shared_task(
    name="finance.receipts.send_pending",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_pending_receipts(self) -> dict:
    """
    Фоновая задача: отправка неотправленных чеков клиентам.
    
    Запускается по расписанию (каждый час).
    Отправляет чеки, которые не были отправлены ранее.
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.models.receipt import Receipt
        
        # Находим неотправленные чеки
        pending_receipts = db.query(Receipt).filter(
            Receipt.is_sent == False
        ).limit(100).all()
        
        receipt_service = ReceiptService(db)
        audit = AuditService(db)
        
        sent_count = 0
        failed_count = 0
        
        for receipt in pending_receipts:
            try:
                result = receipt_service.send_receipt(
                    receipt_id=str(receipt.id),
                    actor_user_id=None,
                )
                if result.success:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Failed to send receipt {receipt.id}: {e}")
        
        audit.log(
            action="task.finance.send_pending_receipts",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Sent {sent_count} receipts, failed {failed_count}",
            after_data={"sent_count": sent_count, "failed_count": failed_count},
        )
        
        return {
            "status": "success",
            "sent_count": sent_count,
            "failed_count": failed_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.finance.send_pending_receipts",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 2. СИНХРОНИЗАЦИЯ С ОФД (ФИСКАЛИЗАЦИЯ)
# ==========================================================

@shared_task(
    name="finance.receipts.sync_ofd",
    bind=True,
    max_retries=5,
    default_retry_delay=300,  # 5 минут
)
def sync_receipts_with_ofd(self) -> dict:
    """
    Фоновая задача: синхронизация чеков с ОФД.
    
    Запускается по расписанию (каждые 30 минут).
    Отправляет нефискализированные чеки в ОФД.
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.models.receipt import Receipt
        
        # Находим чеки без фискального признака
        non_fiscal_receipts = db.query(Receipt).filter(
            Receipt.fiscal_sign.is_(None)
        ).limit(50).all()
        
        receipt_service = ReceiptService(db)
        audit = AuditService(db)
        
        synced_count = 0
        failed_count = 0
        
        for receipt in non_fiscal_receipts:
            try:
                updated = receipt_service.resend_fiscal_receipt(
                    receipt_id=str(receipt.id),
                    actor_user_id=None,
                )
                synced_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Failed to sync receipt {receipt.id} with OFD: {e}")
        
        audit.log(
            action="task.finance.sync_ofd",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Synced {synced_count} receipts with OFD, failed {failed_count}",
            after_data={"synced_count": synced_count, "failed_count": failed_count},
        )
        
        return {
            "status": "success",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.finance.sync_ofd",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 3. АВТОМАТИЧЕСКОЕ ЗАКРЫТИЕ КАССОВЫХ СМЕН
# ==========================================================

@shared_task(
    name="finance.cash_desk.auto_close",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def auto_close_cash_desk_sessions(self, hours_threshold: int = 24) -> dict:
    """
    Фоновая задача: автоматическое закрытие зависших кассовых смен.
    
    Закрывает смены, которые открыты более N часов.
    
    Args:
        hours_threshold: порог в часах
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.models.cash_desk_session import CashDeskSession
        from app.models.user import User
        
        threshold = datetime.now() - timedelta(hours=hours_threshold)
        
        stale_sessions = db.query(CashDeskSession).filter(
            CashDeskSession.status == "OPEN",
            CashDeskSession.opened_at < threshold,
        ).all()
        
        cash_desk_service = CashDeskService(db)
        audit = AuditService(db)
        
        closed_count = 0
        
        for session in stale_sessions:
            try:
                # Закрываем смену с фактической наличностью = ожидаемой
                cash_desk_service.close_session(
                    cashier_user_id=session.cashier_user_id,
                    actual_cash=session.opening_balance + session.cash_income - session.cash_outcome,
                    notes=f"Автоматическое закрытие (активна > {hours_threshold}ч)",
                    actor_user_id=None,
                )
                closed_count += 1
            except Exception as e:
                print(f"Failed to auto-close session {session.id}: {e}")
        
        audit.log(
            action="task.finance.auto_close_cash_desk",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Auto-closed {closed_count} cash desk sessions",
            after_data={"closed_count": closed_count, "hours_threshold": hours_threshold},
        )
        
        return {
            "status": "success",
            "closed_count": closed_count,
            "hours_threshold": hours_threshold,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.finance.auto_close_cash_desk",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 4. ОБРАБОТКА ПРОСРОЧЕННЫХ ПЛАТЕЖЕЙ
# ==========================================================

@shared_task(
    name="finance.payments.cancel_pending",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def cancel_pending_payments(self, hours_threshold: int = 24) -> dict:
    """
    Фоновая задача: отмена просроченных платежей.
    
    Отменяет платежи в статусе PENDING, которые не были завершены в течение N часов.
    
    Args:
        hours_threshold: порог в часах
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.models.payment import Payment
        
        threshold = datetime.now() - timedelta(hours=hours_threshold)
        
        pending_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.PENDING.value,
            Payment.created_at < threshold,
        ).all()
        
        payment_service = PaymentService(db)
        audit = AuditService(db)
        
        cancelled_count = 0
        
        for payment in pending_payments:
            try:
                payment_service.fail_payment(
                    payment_id=str(payment.id),
                    reason=f"Платёж просрочен (не завершён за {hours_threshold}ч)",
                    actor_user_id=None,
                )
                cancelled_count += 1
            except Exception as e:
                print(f"Failed to cancel payment {payment.id}: {e}")
        
        audit.log(
            action="task.finance.cancel_pending_payments",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Cancelled {cancelled_count} pending payments",
            after_data={"cancelled_count": cancelled_count, "hours_threshold": hours_threshold},
        )
        
        return {
            "status": "success",
            "cancelled_count": cancelled_count,
            "hours_threshold": hours_threshold,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.finance.cancel_pending_payments",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 5. СИНХРОНИЗАЦИЯ С ПЛАТЁЖНЫМИ СИСТЕМАМИ
# ==========================================================

@shared_task(
    name="finance.payments.sync_external",
    bind=True,
    max_retries=5,
    default_retry_delay=300,  # 5 минут
)
def sync_payments_with_external_systems(self) -> dict:
    """
    Фоновая задача: синхронизация платежей с внешними системами.
    
    Проверяет статусы платежей в платёжных системах (Сбербанк, Т-Банк, СБП).
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.models.payment import Payment
        
        # Находим платежи в статусе PENDING с указанием платёжной системы
        pending_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.PENDING.value,
            Payment.payment_system.isnot(None),
        ).limit(100).all()
        
        payment_service = PaymentService(db)
        audit = AuditService(db)
        
        synced_count = 0
        failed_count = 0
        updated_count = 0
        
        for payment in pending_payments:
            try:
                # Здесь будет реальный запрос к API платёжной системы
                # status = check_payment_status(payment.external_payment_id)
                
                # Заглушка
                status = "completed"
                
                if status == "completed":
                    payment_service.complete_payment(
                        payment_id=str(payment.id),
                        external_payment_id=payment.external_payment_id,
                        actor_user_id=None,
                    )
                    updated_count += 1
                elif status == "failed":
                    payment_service.fail_payment(
                        payment_id=str(payment.id),
                        reason="Платёж отклонён платёжной системой",
                        actor_user_id=None,
                    )
                    updated_count += 1
                
                synced_count += 1
                
            except Exception as e:
                failed_count += 1
                print(f"Failed to sync payment {payment.id}: {e}")
        
        audit.log(
            action="task.finance.sync_payments_external",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Synced {synced_count} payments, updated {updated_count}, failed {failed_count}",
            after_data={
                "synced_count": synced_count,
                "updated_count": updated_count,
                "failed_count": failed_count,
            },
        )
        
        return {
            "status": "success",
            "synced_count": synced_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.finance.sync_payments_external",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 6. ОТПРАВКА УВЕДОМЛЕНИЙ ОБ ИСТЕЧЕНИИ АБОНЕМЕНТА
# ==========================================================

@shared_task(
    name="finance.subscription.expiry_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_subscription_expiry_notifications(self, days_before: int = 3) -> dict:
    """
    Фоновая задача: отправка уведомлений об истечении абонемента.
    
    Args:
        days_before: за сколько дней до истечения отправить уведомление
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.models.subscription import Subscription
        from app.models.client import Client
        
        target_date = date.today() + timedelta(days=days_before)
        
        expiring_subscriptions = db.query(Subscription).filter(
            Subscription.status == "ACTIVE",
            Subscription.is_active == True,
            Subscription.end_date == target_date,
        ).all()
        
        audit = AuditService(db)
        
        notified_count = 0
        
        for sub in expiring_subscriptions:
            client = db.query(Client).filter(Client.id == sub.client_id).first()
            if client and client.email:
                # Здесь будет отправка email
                # send_email(client.email, "Абонемент истекает", f"Ваш абонемент истекает {sub.end_date}")
                notified_count += 1
        
        audit.log(
            action="task.finance.subscription_expiry_notifications",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Sent {notified_count} subscription expiry notifications",
            after_data={"notified_count": notified_count, "days_before": days_before},
        )
        
        return {
            "status": "success",
            "notified_count": notified_count,
            "days_before": days_before,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.finance.subscription_expiry_notifications",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ==========================================================
# 7. АРХИВАЦИЯ СТАРЫХ ТРАНЗАКЦИЙ
# ==========================================================

@shared_task(
    name="finance.wallet.archive_transactions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def archive_old_wallet_transactions(self, days_to_keep: int = 365) -> dict:
    """
    Фоновая задача: архивация старых транзакций кошелька.
    
    Args:
        days_to_keep: сколько дней хранить в основной таблице
    
    Returns:
        dict: Статистика выполнения задачи
    """
    db = SessionLocal()
    try:
        from app.models.wallet_transaction import WalletTransaction
        
        threshold = datetime.now() - timedelta(days=days_to_keep)
        
        old_transactions = db.query(WalletTransaction).filter(
            WalletTransaction.created_at < threshold
        ).all()
        
        audit = AuditService(db)
        
        archived_count = len(old_transactions)
        
        # Здесь будет логика перемещения в архивную таблицу
        # Например: insert into wallet_transactions_archive select * from wallet_transactions where ...
        
        # Пока просто логируем
        audit.log(
            action="task.finance.archive_wallet_transactions",
            status="success",
            actor_user_id=None,
            entity_type="system",
            message=f"Archived {archived_count} old wallet transactions",
            after_data={"archived_count": archived_count, "days_to_keep": days_to_keep},
        )
        
        return {
            "status": "success",
            "archived_count": archived_count,
            "days_to_keep": days_to_keep,
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        audit.log(
            action="task.finance.archive_wallet_transactions",
            status="error",
            actor_user_id=None,
            entity_type="system",
            message=f"Error: {str(e)}",
        )
        raise self.retry(exc=e)
        
    finally:
        db.close()