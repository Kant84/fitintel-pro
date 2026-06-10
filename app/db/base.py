# app\db\base.py



# импорт функции получения текущего времени с часовым поясом UTC
from datetime import datetime, timezone

# импорт функции создания декларативных ORM-моделей
from sqlalchemy.orm import DeclarativeBase

# импорт средств описания колонок
from sqlalchemy.orm import Mapped, mapped_column

# импорт базовых SQL-типов
from sqlalchemy import DateTime

# импорт типа UUID из PostgreSQL
from sqlalchemy.dialects.postgresql import UUID

# импорт модуля uuid для генерации уникальных идентификаторов
import uuid


# функция, которая возвращает текущее время в UTC
def utc_now() -> datetime:
    # возвращаем текущие дату и время в часовом поясе UTC
    return datetime.now(timezone.utc)


# общий базовый класс для всех ORM-моделей проекта
class Base(DeclarativeBase):
    # здесь пока ничего не добавляем, но именно от этого класса будут наследоваться все модели
    pass


# общий mixin для служебных полей, которые нужны почти всем таблицам
class TimestampedUUIDMixin:
    # первичный ключ типа UUID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),              # PostgreSQL UUID
        primary_key=True,                # первичный ключ
        default=uuid.uuid4,              # по умолчанию генерируем новый UUID
    )

    # дата и время создания записи
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),         # храним дату и время с часовым поясом
        default=utc_now,                 # по умолчанию ставим текущее UTC-время
        nullable=False,                  # поле обязательно
    )

    # дата и время последнего обновления записи
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),         # храним дату и время с часовым поясом
        default=utc_now,                 # первоначально тоже текущее время
        onupdate=utc_now,                # при обновлении автоматически меняется
        nullable=False,                  # поле обязательно
    )