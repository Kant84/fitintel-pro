# app/services/sale_service.py

from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.tariff import Tariff
from app.models.subscription import Subscription
from app.models.visit import Visit
# from app.models.service import Service  # Будет создано позже
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService
from app.services.wallet_service import WalletService
from app.services.receipt_service import ReceiptService
from app.services.subscription_service import SubscriptionService
from app.services.visit_service import VisitService
from app.services.audit_service import AuditService
from app.schemas.sale import (
    SaleSubscriptionRequest,
    SaleSubscriptionResponse,
    SaleServiceRequest,
    SaleServiceResponse,
    SaleVisitRequest,
    SaleVisitResponse,
)
from app.schemas.enums import PaymentMethod, PaymentStatus, ReceiptType, AccessMethod


class SaleService:
    """
    Сервис для продаж.
    
    Включает:
    - Продажу абонементов
    - Продажу дополнительных услуг
    - Продажу разовых посещений
    - Комплексные продажи
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.payment_service = PaymentService(db)
        self.wallet_service = WalletService(db)
        self.receipt_service = ReceiptService(db)
        self.subscription_service = SubscriptionService(db)
        self.visit_service = VisitService(db)
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
    
    def _get_tariff(self, tariff_id: str) -> Tariff:
        """Получить тариф или выбросить 404"""
        tariff = self.db.query(Tariff).filter(Tariff.id == tariff_id).first()
        if not tariff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тариф не найден"
            )
        if not tariff.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тариф неактивен"
            )
        return tariff
    
    def _process_payment(
        self,
        client_id: str,
        amount: Decimal,
        payment_method: str,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> dict:
        """
        Обработать платёж.
        
        Returns:
            Словарь с информацией о платеже
        """
        # Оплата с баланса кошелька
        if payment_method == PaymentMethod.BALANCE.value:
            self.wallet_service.withdraw(
                client_id=client_id,
                amount=amount,
                description=f"Оплата услуг",
                reference_type="sale",
                actor_user_id=actor_user_id,
            )
            payment_id = None
        
        # Наличные, карта, СБП
        else:
            payment = self.payment_service.create_payment(
                client_id=client_id,
                amount=amount,
                payment_method=PaymentMethod(payment_method),
                notes=notes,
                actor_user_id=actor_user_id,
            )
            payment = self.payment_service.complete_payment(
                payment_id=str(payment.id),
                actor_user_id=actor_user_id,
            )
            payment_id = payment.id
        
        return {
            "payment_id": payment_id,
            "amount": amount,
            "payment_method": payment_method,
        }
    
    def _generate_receipt(
        self,
        payment_id: str | None,
        amount: Decimal,
        client: Client,
        receipt_type: str = ReceiptType.SALE.value,
        actor_user_id: str | None = None,
    ) -> Optional[str]:
        """Сгенерировать чек для продажи"""
        if not payment_id:
            return None
        
        receipt = self.receipt_service.generate_receipt(
            payment_id=payment_id,
            receipt_type=ReceiptType(receipt_type),
            customer_email=client.email,
            customer_phone=client.phone,
            actor_user_id=actor_user_id,
        )
        
        return str(receipt.id)
    
    # ==========================================================
    # ПРОДАЖА АБОНЕМЕНТА
    # ==========================================================
    
    def sell_subscription(
        self,
        request: SaleSubscriptionRequest,
        actor_user_id: str | None = None,
    ) -> SaleSubscriptionResponse:
        """
        Продажа абонемента клиенту.
        """
        client = self._get_client(str(request.client_id))
        tariff = self._get_tariff(str(request.tariff_id))
        
        start_date = request.start_date or date.today()
        end_date = start_date + timedelta(days=tariff.duration_days)
        
        # Обработка платежа
        payment_result = self._process_payment(
            client_id=str(request.client_id),
            amount=tariff.price,
            payment_method=request.payment_method,
            notes=f"Покупка абонемента: {tariff.name}",
            actor_user_id=actor_user_id,
        )
        
        # Создаём абонемент
        subscription = Subscription(
            client_id=str(request.client_id),
            tariff_id=str(request.tariff_id),
            status="ACTIVE",
            start_date=start_date,
            end_date=end_date,
            price=tariff.price,
            currency=tariff.currency,
            visit_limit=tariff.visit_limit,
            visits_used=0,
            is_unlimited=tariff.is_unlimited,
            is_active=True,
            auto_renew=request.auto_renew,
            notes=request.notes,
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        # Генерируем чек
        receipt_id = self._generate_receipt(
            payment_id=payment_result["payment_id"],
            amount=tariff.price,
            client=client,
            actor_user_id=actor_user_id,
        )
        
        # Логируем продажу
        self.audit.log(
            action="sale.subscription",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="subscription",
            entity_id=subscription.id,
            message=f"Subscription sold to client {client.email}: {tariff.name} for {tariff.price} RUB",
            after_data={
                "client_id": str(request.client_id),
                "tariff_id": str(request.tariff_id),
                "tariff_name": tariff.name,
                "price": str(tariff.price),
                "payment_method": request.payment_method,
                "subscription_id": str(subscription.id),
            },
        )
        
        return SaleSubscriptionResponse(
            success=True,
            subscription_id=subscription.id,
            payment_id=payment_result["payment_id"],
            receipt_id=receipt_id,
            amount=tariff.price,
            message=f"Абонемент «{tariff.name}» успешно приобретён",
        )
    
    # ==========================================================
    # ПРОДАЖА УСЛУГИ
    # ==========================================================
    
    def sell_service(
        self,
        request: SaleServiceRequest,
        actor_user_id: str | None = None,
    ) -> SaleServiceResponse:
        """
        Продажа дополнительной услуги.
        """
        client = self._get_client(str(request.client_id))
        
        # TODO: Получить услугу из БД
        price = Decimal("500.00") * request.quantity
        service_name = "Дополнительная услуга"
        
        # Обработка платежа
        payment_result = self._process_payment(
            client_id=str(request.client_id),
            amount=price,
            payment_method=request.payment_method,
            notes=f"Покупка услуги: {service_name} x{request.quantity}",
            actor_user_id=actor_user_id,
        )
        
        # TODO: Создать запись о продаже услуги
        
        # Генерируем чек
        receipt_id = self._generate_receipt(
            payment_id=payment_result["payment_id"],
            amount=price,
            client=client,
            actor_user_id=actor_user_id,
        )
        
        self.audit.log(
            action="sale.service",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="sale",
            message=f"Service sold to client {client.email}: {service_name} x{request.quantity} for {price} RUB",
            after_data={
                "client_id": str(request.client_id),
                "service_name": service_name,
                "quantity": request.quantity,
                "price": str(price),
                "payment_method": request.payment_method,
            },
        )
        
        return SaleServiceResponse(
            success=True,
            sale_id=None,
            payment_id=payment_result["payment_id"],
            receipt_id=receipt_id,
            amount=price,
            message=f"Услуга «{service_name}» успешно приобретена",
        )
    
    # ==========================================================
    # ПРОДАЖА РАЗОВОГО ПОСЕЩЕНИЯ
    # ==========================================================
    
    def sell_visit(
        self,
        request: SaleVisitRequest,
        actor_user_id: str | None = None,
    ) -> SaleVisitResponse:
        """
        Продажа разового посещения.
        """
        client = self._get_client(str(request.client_id))
        
        # Цена разового посещения
        price = Decimal("800.00")
        
        # Обработка платежа
        payment_result = self._process_payment(
            client_id=str(request.client_id),
            amount=price,
            payment_method=request.payment_method,
            notes=f"Разовое посещение. Зона: {request.zone or 'общая'}",
            actor_user_id=actor_user_id,
        )
        
        # Создаём разовое посещение (без абонемента)
        visit = self.visit_service.entry(
            client_id=str(request.client_id),
            subscription_id=None,
            access_method=AccessMethod.MANUAL,
            zone=request.zone,
            notes=f"Разовое посещение. Оплачено: {price} RUB",
            actor_user_id=actor_user_id,
        )
        
        # Сразу закрываем посещение
        completed_visit = self.visit_service.exit(
            visit_id=str(visit.id),
            actor_user_id=actor_user_id,
        )
        
        # Генерируем чек
        receipt_id = self._generate_receipt(
            payment_id=payment_result["payment_id"],
            amount=price,
            client=client,
            actor_user_id=actor_user_id,
        )
        
        self.audit.log(
            action="sale.visit",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="visit",
            entity_id=visit.id,
            message=f"Single visit sold to client {client.email} for {price} RUB",
            after_data={
                "client_id": str(request.client_id),
                "zone": request.zone,
                "price": str(price),
                "payment_method": request.payment_method,
                "visit_id": str(visit.id),
            },
        )
        
        return SaleVisitResponse(
            success=True,
            visit_id=visit.id,
            payment_id=payment_result["payment_id"],
            receipt_id=receipt_id,
            amount=price,
            message=f"Разовое посещение успешно оплачено",
        )
    
    # ==========================================================
    # КОМПЛЕКСНАЯ ПРОДАЖА
    # ==========================================================
    
    def sell_package(
        self,
        client_id: str,
        items: list[dict],
        payment_method: str,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> dict:
        """
        Комплексная продажа (несколько товаров/услуг одним чеком).
        """
        client = self._get_client(client_id)
        total_amount = Decimal("0.00")
        results = []
        
        # Считаем общую сумму
        for item in items:
            price = Decimal(str(item.get("price", 0)))
            quantity = item.get("quantity", 1)
            total_amount += price * quantity
        
        # Обработка общего платежа
        payment_result = self._process_payment(
            client_id=client_id,
            amount=total_amount,
            payment_method=payment_method,
            notes=notes,
            actor_user_id=actor_user_id,
        )
        
        # Продажа каждого товара/услуги
        for item in items:
            item_type = item.get("type")
            
            if item_type == "subscription":
                result = self.sell_subscription(
                    SaleSubscriptionRequest(
                        client_id=UUID(client_id),
                        tariff_id=UUID(item["tariff_id"]),
                        payment_method=payment_method,
                        auto_renew=item.get("auto_renew", False),
                        notes=item.get("notes"),
                    ),
                    actor_user_id=actor_user_id,
                )
                results.append(result.model_dump())
            
            elif item_type == "service":
                result = self.sell_service(
                    SaleServiceRequest(
                        client_id=UUID(client_id),
                        service_id=UUID(item["service_id"]),
                        quantity=item.get("quantity", 1),
                        payment_method=payment_method,
                        notes=item.get("notes"),
                    ),
                    actor_user_id=actor_user_id,
                )
                results.append(result.model_dump())
            
            elif item_type == "visit":
                result = self.sell_visit(
                    SaleVisitRequest(
                        client_id=UUID(client_id),
                        zone=item.get("zone"),
                        payment_method=payment_method,
                        notes=item.get("notes"),
                    ),
                    actor_user_id=actor_user_id,
                )
                results.append(result.model_dump())
        
        # Генерируем общий чек
        receipt_id = self._generate_receipt(
            payment_id=payment_result["payment_id"],
            amount=total_amount,
            client=client,
            actor_user_id=actor_user_id,
        )
        
        self.audit.log(
            action="sale.package",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="sale",
            message=f"Package sale to client {client.email}: {len(items)} items, total {total_amount} RUB",
            after_data={
                "client_id": client_id,
                "items_count": len(items),
                "total_amount": str(total_amount),
                "payment_method": payment_method,
            },
        )
        
        return {
            "success": True,
            "payment_id": payment_result["payment_id"],
            "receipt_id": receipt_id,
            "total_amount": total_amount,
            "items": results,
            "message": f"Продажа {len(items)} позиций на сумму {total_amount} RUB успешно завершена",
        }