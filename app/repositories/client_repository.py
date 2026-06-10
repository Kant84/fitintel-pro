# app/repositories/client_repository.py

# импорт select из SQLAlchemy
from sqlalchemy import select

# импорт Session и типизации
from sqlalchemy.orm import Session

# импорт модели клиента
from app.models.client import Client


# репозиторий клиентов
class ClientRepository:
    # конструктор принимает активную SQLAlchemy-сессию
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

    # метод получает клиента по id
    def get_by_id(self, client_id: str) -> Client | None:
        # собираем SQL-запрос
        statement = select(Client).where(Client.id == client_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем объект клиента или None
        return result.scalar_one_or_none()

    # метод получает список клиентов
    def list_clients(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Client]:
        # собираем SQL-запрос
        statement = (
            select(Client)
            # сортируем сначала по дате создания от новых к старым
            .order_by(Client.created_at.desc())
            # применяем смещение
            .offset(offset)
            # применяем лимит
            .limit(limit)
        )

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем список клиентов
        return list(result.scalars().all())

    # метод ищет клиента по email
    def get_by_email(self, email: str) -> Client | None:
        # собираем SQL-запрос
        statement = select(Client).where(Client.email == email)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем клиента или None
        return result.scalar_one_or_none()

    # метод ищет клиента по телефону
    def get_by_phone(self, phone: str) -> Client | None:
        # собираем SQL-запрос
        statement = select(Client).where(Client.phone == phone)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем клиента или None
        return result.scalar_one_or_none()

    # метод проверяет, занят ли email
    def email_exists(
        self,
        email: str,
        exclude_client_id: str | None = None,
    ) -> bool:
        # создаём базовый запрос
        statement = select(Client).where(Client.email == email)

        # если нужно исключить текущего клиента — добавляем условие
        if exclude_client_id is not None:
            statement = statement.where(Client.id != exclude_client_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # если клиент найден — email уже занят
        return result.scalar_one_or_none() is not None

    # метод проверяет, занят ли телефон
    def phone_exists(
        self,
        phone: str,
        exclude_client_id: str | None = None,
    ) -> bool:
        # создаём базовый запрос
        statement = select(Client).where(Client.phone == phone)

        # если нужно исключить текущего клиента — добавляем условие
        if exclude_client_id is not None:
            statement = statement.where(Client.id != exclude_client_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # если клиент найден — телефон уже занят
        return result.scalar_one_or_none() is not None

    # метод добавляет клиента в БД
    def add(self, client: Client) -> Client:
        # добавляем объект в сессию
        self.db.add(client)

        # сохраняем изменения
        self.db.commit()

        # перечитываем объект из базы
        self.db.refresh(client)

        # возвращаем клиента
        return client

    # метод сохраняет изменения существующего клиента
    def save(self, client: Client) -> Client:
        # сохраняем изменения
        self.db.commit()

        # перечитываем объект
        self.db.refresh(client)

        # возвращаем клиента
        return client