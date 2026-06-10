# app\db\session.py
# импорт функции создания engine
from sqlalchemy import create_engine

# импорт фабрики сессий
from sqlalchemy.orm import sessionmaker

# импорт настроек проекта
from app.core.config import settings


# создаём engine SQLAlchemy для подключения к PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,          # строка подключения к базе данных
    echo=settings.APP_DEBUG,        # показывать SQL-запросы в режиме отладки
    pool_pre_ping=True,             # проверять соединение перед использованием
    connect_args={
        "connect_timeout": 5        # ждать подключения не дольше 5 секунд
    },
)


# создаём фабрику сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# функция выдачи сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()