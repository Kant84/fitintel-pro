# app/repositories/subscription_repository.py

# импорт select
from sqlalchemy import select

# импорт Session
from sqlalchemy.orm import Session

# импорт модели абонемента
from app.models.subscription import Subscription


class SubscriptionRepository:
    # конструктор
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

    # получить по id
    def get_by_id(self, subscription_id: str) -> Subscription | None:
        # собираем запрос
        statement = select(Subscription).where(Subscription.id == subscription_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем объект или None
        return result.scalar_one_or_none()

    # список абонементов
    def list_subscriptions(self, offset: int = 0, limit: int = 100) -> list[Subscription]:
        # собираем запрос
        statement = (
            select(Subscription)
            .order_by(Subscription.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем список
        return list(result.scalars().all())

    # добавить абонемент
    def add(self, subscription: Subscription) -> Subscription:
        # добавляем в сессию
        self.db.add(subscription)

        # коммитим
        self.db.commit()

        # перечитываем
        self.db.refresh(subscription)

        # возвращаем объект
        return subscription

    # сохранить изменения
    def save(self, subscription: Subscription) -> Subscription:
        # коммитим
        self.db.commit()

        # перечитываем
        self.db.refresh(subscription)

        # возвращаем объект
        return subscription