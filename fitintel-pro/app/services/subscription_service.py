# app/services/subscription_service.py

# импорт timedelta
from datetime import timedelta

# импорт HTTPException и status
from fastapi import HTTPException, status

# импорт Session
from sqlalchemy.orm import Session

# импорт моделей
from app.models.subscription import Subscription
from app.models.client import Client
from app.models.tariff import Tariff

# импорт репозитория
from app.repositories.subscription_repository import SubscriptionRepository

# импорт сервиса аудита
from app.services.audit_service import AuditService

# импорт нормализации текста
from app.utils.validators import normalize_text


# допустимые статусы абонемента
SUBSCRIPTION_STATUSES = {
    "DRAFT",
    "ACTIVE",
    "EXPIRED",
    "FROZEN",
}


class SubscriptionService:
    # конструктор
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

        # создаём репозиторий
        self.subscription_repository = SubscriptionRepository(db)

        # создаём аудит
        self.audit = AuditService(db)

    # нормализуем статус
    def normalize_status(self, status_value: str) -> str:
        # убираем пробелы и переводим в верхний регистр
        normalized = status_value.strip().upper()

        # если статус пустой — ошибка
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Статус абонемента не может быть пустым",
            )

        # если статус не поддерживается — ошибка
        if normalized not in SUBSCRIPTION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недопустимый статус абонемента. Допустимые значения: DRAFT, ACTIVE, EXPIRED, FROZEN",
            )

        # возвращаем статус
        return normalized

    # переводим статус в is_active
    def status_to_is_active(self, subscription_status: str) -> bool:
        # активным считается только ACTIVE
        return subscription_status == "ACTIVE"

    # получаем клиента
    def get_client(self, client_id: str) -> Client:
        # ищем клиента
        client = self.db.get(Client, client_id)

        # если не найден — ошибка
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )

        # возвращаем клиента
        return client

    # получаем тариф
    def get_tariff(self, tariff_id: str) -> Tariff:
        # ищем тариф
        tariff = self.db.get(Tariff, tariff_id)

        # если не найден — ошибка
        if tariff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тариф не найден",
            )

        # возвращаем тариф
        return tariff

    # получить абонемент по id
    def get_subscription_by_id(self, subscription_id: str) -> Subscription:
        # ищем абонемент
        subscription = self.subscription_repository.get_by_id(subscription_id)

        # если не найден — ошибка
        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Абонемент не найден",
            )

        # возвращаем объект
        return subscription

    # список абонементов
    def list_subscriptions(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        actor_user_id=None,
    ) -> list[Subscription]:
        # получаем список
        subscriptions = self.subscription_repository.list_subscriptions(
            offset=offset,
            limit=limit,
        )

        # пишем аудит
        self.audit.log(
            action="crm.subscription.list",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="subscription",
            message="Subscription list requested",
            after_data={
                "offset": offset,
                "limit": limit,
                "count": len(subscriptions),
            },
        )

        # возвращаем список
        return subscriptions

    # создать абонемент
    def create_subscription(
        self,
        *,
        client_id: str,
        tariff_id: str,
        start_date,
        status_value: str,
        notes: str | None,
        actor_user_id=None,
    ) -> Subscription:
        # получаем клиента
        client = self.get_client(client_id)

        # получаем тариф
        tariff = self.get_tariff(tariff_id)

        # нормализуем статус
        normalized_status = self.normalize_status(status_value)

        # рассчитываем флаг активности
        resolved_is_active = self.status_to_is_active(normalized_status)

        # вычисляем дату окончания
        end_date = start_date + timedelta(days=tariff.duration_days)

        # нормализуем заметки
        normalized_notes = normalize_text(notes) if notes else None

        # создаём абонемент
        subscription = Subscription(
            client_id=client.id,
            tariff_id=tariff.id,
            status=normalized_status,
            start_date=start_date,
            end_date=end_date,
            price=tariff.price,
            currency=tariff.currency,
            visit_limit=tariff.visit_limit,
            visits_used=0,
            is_unlimited=tariff.is_unlimited,
            is_active=resolved_is_active,
            notes=normalized_notes,
        )

        # сохраняем
        created_subscription = self.subscription_repository.add(subscription)

        # пишем аудит
        self.audit.log(
            action="crm.subscription.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="subscription",
            entity_id=created_subscription.id,
            message="Subscription created successfully",
            after_data={
                "id": created_subscription.id,
                "client_id": str(created_subscription.client_id),
                "tariff_id": str(created_subscription.tariff_id),
                "status": created_subscription.status,
                "start_date": str(created_subscription.start_date),
                "end_date": str(created_subscription.end_date),
                "price": str(created_subscription.price),
                "currency": created_subscription.currency,
                "visit_limit": created_subscription.visit_limit,
                "visits_used": created_subscription.visits_used,
                "is_unlimited": created_subscription.is_unlimited,
                "is_active": created_subscription.is_active,
            },
        )

        # возвращаем абонемент
        return created_subscription

    # обновить абонемент
    def update_subscription(
        self,
        *,
        subscription_id: str,
        status_value: str | None = None,
        start_date=None,
        end_date=None,
        visits_used: int | None = None,
        notes: str | None = None,
        actor_user_id=None,
    ) -> Subscription:
        # получаем абонемент
        subscription = self.get_subscription_by_id(subscription_id)

        # before_data
        before_data = {
            "id": subscription.id,
            "client_id": str(subscription.client_id),
            "tariff_id": str(subscription.tariff_id),
            "status": subscription.status,
            "start_date": str(subscription.start_date),
            "end_date": str(subscription.end_date),
            "price": str(subscription.price),
            "currency": subscription.currency,
            "visit_limit": subscription.visit_limit,
            "visits_used": subscription.visits_used,
            "is_unlimited": subscription.is_unlimited,
            "is_active": subscription.is_active,
            "notes": subscription.notes,
        }

        # обновляем статус
        if status_value is not None:
            normalized_status = self.normalize_status(status_value)
            subscription.status = normalized_status
            subscription.is_active = self.status_to_is_active(normalized_status)

        # обновляем start_date
        if start_date is not None:
            subscription.start_date = start_date

        # обновляем end_date
        if end_date is not None:
            subscription.end_date = end_date

        # обновляем visits_used
        if visits_used is not None:
            if visits_used < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="visits_used не может быть меньше 0",
                )

            subscription.visits_used = visits_used

            # если абонемент не безлимитный и лимит исчерпан — переводим в EXPIRED
            if (
                not subscription.is_unlimited
                and subscription.visit_limit is not None
                and subscription.visits_used >= subscription.visit_limit
            ):
                subscription.status = "EXPIRED"
                subscription.is_active = False

        # обновляем notes
        if notes is not None:
            subscription.notes = normalize_text(notes) if notes else None

        # сохраняем
        updated_subscription = self.subscription_repository.save(subscription)

        # аудит
        self.audit.log(
            action="crm.subscription.updated",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="subscription",
            entity_id=updated_subscription.id,
            message="Subscription updated successfully",
            before_data=before_data,
            after_data={
                "id": updated_subscription.id,
                "client_id": str(updated_subscription.client_id),
                "tariff_id": str(updated_subscription.tariff_id),
                "status": updated_subscription.status,
                "start_date": str(updated_subscription.start_date),
                "end_date": str(updated_subscription.end_date),
                "price": str(updated_subscription.price),
                "currency": updated_subscription.currency,
                "visit_limit": updated_subscription.visit_limit,
                "visits_used": updated_subscription.visits_used,
                "is_unlimited": updated_subscription.is_unlimited,
                "is_active": updated_subscription.is_active,
                "notes": updated_subscription.notes,
            },
        )

        # возвращаем абонемент
        return updated_subscription

    # собираем response
    def build_subscription_response(self, subscription: Subscription) -> dict:
        # возвращаем словарь
        return {
            "id": subscription.id,
            "client_id": subscription.client_id,
            "tariff_id": subscription.tariff_id,
            "status": subscription.status,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "price": subscription.price,
            "currency": subscription.currency,
            "visit_limit": subscription.visit_limit,
            "visits_used": subscription.visits_used,
            "is_unlimited": subscription.is_unlimited,
            "is_active": subscription.is_active,
            "notes": subscription.notes,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
        }

    # собираем response списка
    def build_subscription_list_response(self, subscriptions: list[Subscription]) -> dict:
        # собираем элементы
        items = [self.build_subscription_response(item) for item in subscriptions]

        # возвращаем структуру
        return {
            "items": items,
            "count": len(items),
        }