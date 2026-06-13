# app/services/receipt_service.py

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
import hashlib
import json
import qrcode
import io
import base64
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.receipt import Receipt
from app.models.payment import Payment
from app.models.client import Client
from app.repositories.receipt_repository import ReceiptRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.audit_service import AuditService
from app.schemas.receipt import (
    ReceiptResponse,
    ReceiptSendRequest,
    ReceiptSendResponse,
    ReceiptGenerateRequest,
)
from app.schemas.enums import ReceiptType, PaymentMethod


class ReceiptService:
    """
    Сервис для управления чеками.
    
    Включает:
    - Генерацию чеков (фискальных и нефискальных)
    - Интеграцию с ОФД (заглушка)
    - Отправку чеков на email/SMS
    - Генерацию QR-кодов чеков
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.receipt_repo = ReceiptRepository(db)
        self.payment_repo = PaymentRepository(db)
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
    
    def _get_payment(self, payment_id: str) -> Payment:
        """Получить платёж или выбросить 404"""
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Платёж не найден"
            )
        return payment
    
    def _generate_receipt_number(self) -> str:
        """Сгенерировать уникальный номер чека"""
        import uuid
        return f"RCP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    
    def _generate_qr_code(self, receipt_data: dict) -> str:
        """
        Сгенерировать QR-код для чека.
        
        Формат: https://ofd.ru/check/{receipt_number}
        """
        qr_data = f"https://ofd.example.com/check/{receipt_data.get('receipt_number')}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _build_receipt_data(
        self,
        payment: Payment,
        receipt_type: str,
        receipt_number: str,
    ) -> dict:
        """Построить данные для чека"""
        client = self._get_client(payment.client_id)
        
        return {
            "receipt_number": receipt_number,
            "receipt_type": receipt_type,
            "payment_id": str(payment.id),
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_date": payment.paid_at or payment.created_at,
            "client": {
                "name": f"{client.first_name} {client.last_name}",
                "email": client.email,
                "phone": client.phone,
            },
            "items": [],  # В будущем добавим товары/услуги
        }
    
    def _send_to_ofd(self, receipt_data: dict) -> dict:
        """
        Отправить чек в ОФД (фискализация).
        
        В реальности здесь будет запрос к API ОФД.
        Пока возвращает заглушку.
        """
        # Заглушка для разработки
        return {
            "fiscal_sign": hashlib.md5(
                f"{receipt_data['receipt_number']}{receipt_data['amount']}".encode()
            ).hexdigest()[:16],
            "fiscal_document_number": 1001,
            "fiscal_document_date": datetime.now(),
            "ofd_url": f"https://ofd.example.com/check/{receipt_data['receipt_number']}",
        }
    
    # ==========================================================
    # ОСНОВНЫЕ ОПЕРАЦИИ
    # ==========================================================
    
    def generate_receipt(
        self,
        payment_id: str,
        receipt_type: ReceiptType = ReceiptType.SALE,
        customer_email: str | None = None,
        customer_phone: str | None = None,
        actor_user_id: str | None = None,
    ) -> Receipt:
        """
        Сгенерировать чек для платежа.
        
        Args:
            payment_id: ID платежа
            receipt_type: Тип чека (SALE, REFUND)
            customer_email: Email клиента (для отправки)
            customer_phone: Телефон клиента (для SMS)
            actor_user_id: Кто сгенерировал
        
        Returns:
            Сгенерированный чек
        """
        payment = self._get_payment(payment_id)
        
        # Проверяем, не существует ли уже чек для этого платежа
        existing = self.receipt_repo.get_by_payment_id(payment_id)
        if existing:
            return existing
        
        receipt_number = self._generate_receipt_number()
        client = self._get_client(payment.client_id)
        
        # Формируем данные чека
        receipt_data = self._build_receipt_data(payment, receipt_type.value, receipt_number)
        
        # Отправляем в ОФД (фискализация)
        ofd_data = self._send_to_ofd(receipt_data)
        
        # Генерируем QR-код
        qr_code = self._generate_qr_code(receipt_data)
        
        # Создаём чек
        receipt = Receipt(
            payment_id=payment_id,
            receipt_number=receipt_number,
            receipt_type=receipt_type.value,
            fiscal_sign=ofd_data.get("fiscal_sign"),
            fiscal_document_number=ofd_data.get("fiscal_document_number"),
            fiscal_document_date=ofd_data.get("fiscal_document_date"),
            ofd_url=ofd_data.get("ofd_url"),
            qr_code=qr_code,
            customer_email=customer_email or client.email,
            customer_phone=customer_phone or client.phone,
            is_sent=False,
        )
        
        created_receipt = self.receipt_repo.add(receipt)
        
        self.audit.log(
            action="receipt.generated",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="receipt",
            entity_id=created_receipt.id,
            message=f"Receipt {receipt_number} generated for payment {payment_id}",
            after_data={
                "payment_id": payment_id,
                "receipt_type": receipt_type.value,
                "amount": str(payment.amount),
            },
        )
        
        return created_receipt
    
    def get_receipt(self, receipt_id: str) -> Receipt:
        """Получить чек по ID"""
        receipt = self.receipt_repo.get_by_id(receipt_id)
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Чек не найден"
            )
        return receipt
    
    def get_receipt_by_payment(self, payment_id: str) -> Receipt:
        """Получить чек по ID платежа"""
        receipt = self.receipt_repo.get_by_payment_id(payment_id)
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Чек для этого платежа не найден"
            )
        return receipt
    
    def get_receipt_by_number(self, receipt_number: str) -> Receipt:
        """Получить чек по номеру"""
        receipt = self.receipt_repo.get_by_number(receipt_number)
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Чек не найден"
            )
        return receipt
    
    def _build_response(self, receipt: Receipt) -> dict:
        """Построить ответ чека"""
        return {
            "id": receipt.id,
            "payment_id": receipt.payment_id,
            "receipt_number": receipt.receipt_number,
            "receipt_type": receipt.receipt_type,
            "fiscal_sign": receipt.fiscal_sign,
            "fiscal_document_number": receipt.fiscal_document_number,
            "fiscal_document_date": receipt.fiscal_document_date,
            "ofd_url": receipt.ofd_url,
            "qr_code": receipt.qr_code,
            "customer_email": receipt.customer_email,
            "customer_phone": receipt.customer_phone,
            "is_sent": receipt.is_sent,
            "created_at": receipt.created_at,
        }
    
    # ==========================================================
    # ОТПРАВКА ЧЕКОВ
    # ==========================================================
    
    def send_receipt(
        self,
        receipt_id: str,
        email: str | None = None,
        phone: str | None = None,
        send_sms: bool = False,
        actor_user_id: str | None = None,
    ) -> ReceiptSendResponse:
        """
        Отправить чек клиенту.
        
        Поддерживает:
        - Email
        - SMS (через внешнего провайдера)
        """
        receipt = self.get_receipt(receipt_id)
        payment = self._get_payment(receipt.payment_id)
        client = self._get_client(payment.client_id)
        
        sent_to = []
        
        # Формируем содержимое чека
        receipt_data = self._build_receipt_data(
            payment, receipt.receipt_type, receipt.receipt_number
        )
        
        # Отправка на email
        target_email = email or receipt.customer_email or client.email
        if target_email:
            try:
                self._send_email_receipt(target_email, receipt_data, receipt.qr_code)
                sent_to.append(f"email:{target_email}")
            except Exception as e:
                print(f"Failed to send email receipt: {e}")
        
        # Отправка SMS
        if send_sms:
            target_phone = phone or receipt.customer_phone or client.phone
            if target_phone:
                try:
                    self._send_sms_receipt(target_phone, receipt_data)
                    sent_to.append(f"sms:{target_phone}")
                except Exception as e:
                    print(f"Failed to send SMS receipt: {e}")
        
        # Отмечаем чек как отправленный
        if sent_to:
            receipt.is_sent = True
            self.receipt_repo.save(receipt)
        
        self.audit.log(
            action="receipt.sent",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="receipt",
            entity_id=receipt.id,
            message=f"Receipt {receipt.receipt_number} sent to {', '.join(sent_to)}",
        )
        
        return ReceiptSendResponse(
            success=len(sent_to) > 0,
            sent_to=sent_to,
            message=f"Чек отправлен на {', '.join(sent_to)}" if sent_to else "Не удалось отправить чек",
        )
    
    def _send_email_receipt(self, email: str, receipt_data: dict, qr_code: str) -> None:
        """
        Отправить чек на email.
        
        В реальности здесь будет отправка через SMTP или email-сервис.
        """
        # Заглушка для разработки
        print(f"[EMAIL] Sending receipt to {email}")
        print(f"[EMAIL] Receipt number: {receipt_data['receipt_number']}")
        print(f"[EMAIL] Amount: {receipt_data['amount']} {receipt_data['currency']}")
    
    def _send_sms_receipt(self, phone: str, receipt_data: dict) -> None:
        """
        Отправить SMS с информацией о чеке.
        
        В реальности здесь будет запрос к SMS-провайдеру.
        """
        # Заглушка для разработки
        print(f"[SMS] Sending receipt info to {phone}")
        print(f"[SMS] Receipt number: {receipt_data['receipt_number']}")
        print(f"[SMS] Amount: {receipt_data['amount']} {receipt_data['currency']}")
    
    # ==========================================================
    # PDF ГЕНЕРАЦИЯ (опционально)
    # ==========================================================
    
    def generate_pdf(self, receipt_id: str) -> bytes:
        """
        Сгенерировать PDF-версию чека.
        
        Returns:
            PDF-файл в виде bytes
        """
        receipt = self.get_receipt(receipt_id)
        payment = self._get_payment(receipt.payment_id)
        client = self._get_client(payment.client_id)
        
        receipt_data = self._build_receipt_data(
            payment, receipt.receipt_type, receipt.receipt_number
        )
        
        # Здесь будет генерация PDF через jinja2 + weasyprint
        # Пока возвращаем заглушку
        pdf_content = f"""
        PDF Receipt
        ===========
        Receipt: {receipt.receipt_number}
        Date: {receipt.created_at}
        Client: {client.first_name} {client.last_name}
        Amount: {payment.amount} {payment.currency}
        Payment method: {payment.payment_method}
        """
        
        return pdf_content.encode()
    
    # ==========================================================
    # АДМИНИСТРИРОВАНИЕ
    # ==========================================================
    
    def resend_fiscal_receipt(self, receipt_id: str, actor_user_id: str | None = None) -> Receipt:
        """
        Повторно отправить чек в ОФД (если не прошла фискализация).
        """
        receipt = self.get_receipt(receipt_id)
        payment = self._get_payment(receipt.payment_id)
        
        receipt_data = self._build_receipt_data(
            payment, receipt.receipt_type, receipt.receipt_number
        )
        
        # Повторная отправка в ОФД
        ofd_data = self._send_to_ofd(receipt_data)
        
        # Обновляем фискальные данные
        receipt.fiscal_sign = ofd_data.get("fiscal_sign")
        receipt.fiscal_document_number = ofd_data.get("fiscal_document_number")
        receipt.fiscal_document_date = ofd_data.get("fiscal_document_date")
        receipt.ofd_url = ofd_data.get("ofd_url")
        
        updated_receipt = self.receipt_repo.save(receipt)
        
        self.audit.log(
            action="receipt.resend_fiscal",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="receipt",
            entity_id=receipt.id,
            message=f"Fiscal receipt {receipt.receipt_number} resent to OFD",
        )
        
        return updated_receipt