# app/repositories/tariff_repository.py

# импорт select
from sqlalchemy import select

# импорт Session
from sqlalchemy.orm import Session

# импорт модели тарифа
from app.models.tariff import Tariff


class TariffRepository:
    # конструктор принимает сессию БД
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

    # получить тариф по id
    def get_by_id(self, tariff_id: str) -> Tariff | None:
        # собираем запрос
        statement = select(Tariff).where(Tariff.id == tariff_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем тариф или None
        return result.scalar_one_or_none()

    # получить тариф по code
    def get_by_code(self, code: str) -> Tariff | None:
        # собираем запрос
        statement = select(Tariff).where(Tariff.code == code)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем тариф или None
        return result.scalar_one_or_none()

    # получить тариф по name
    def get_by_name(self, name: str) -> Tariff | None:
        # собираем запрос
        statement = select(Tariff).where(Tariff.name == name)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем тариф или None
        return result.scalar_one_or_none()

    # список тарифов
    def list_tariffs(self, offset: int = 0, limit: int = 100) -> list[Tariff]:
        # собираем запрос
        statement = (
            select(Tariff)
            .order_by(Tariff.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем список
        return list(result.scalars().all())

    # проверить занятость code
    def code_exists(self, code: str, exclude_tariff_id: str | None = None) -> bool:
        # создаём базовый запрос
        statement = select(Tariff).where(Tariff.code == code)

        # исключаем текущий тариф, если нужно
        if exclude_tariff_id is not None:
            statement = statement.where(Tariff.id != exclude_tariff_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # True если найден
        return result.scalar_one_or_none() is not None

    # проверить занятость name
    def name_exists(self, name: str, exclude_tariff_id: str | None = None) -> bool:
        # создаём базовый запрос
        statement = select(Tariff).where(Tariff.name == name)

        # исключаем текущий тариф, если нужно
        if exclude_tariff_id is not None:
            statement = statement.where(Tariff.id != exclude_tariff_id)

        # выполняем запрос
        result = self.db.execute(statement)

        # True если найден
        return result.scalar_one_or_none() is not None

    # добавить тариф
    def add(self, tariff: Tariff) -> Tariff:
        # добавляем в сессию
        self.db.add(tariff)

        # коммитим
        self.db.commit()

        # перечитываем объект
        self.db.refresh(tariff)

        # возвращаем тариф
        return tariff

    # сохранить тариф
    def save(self, tariff: Tariff) -> Tariff:
        # коммитим
        self.db.commit()

        # перечитываем объект
        self.db.refresh(tariff)

        # возвращаем тариф
        return tariff