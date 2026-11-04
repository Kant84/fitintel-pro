## app/db/session.py
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
    pool_size=20,                   # W5: запас под опросы десктопа/healthcheck/свип
    max_overflow=20,                # пиковый overflow (было 10 -> QueuePool timeout)
    pool_timeout=10,                # не ждать соединение дольше 10 сек
    pool_recycle=1800,              # пересоздавать соединения раз в 30 мин
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


# ---------------------------------------------------------------------------
# Глобальная защита от повторного идемпотентного DDL на горячем пути.
# ALTER/CREATE ... IF NOT EXISTS берет тяжелые блокировки ДАЖЕ когда объект
# уже существует; 20+ таких вызовов на запрос конвоем сериализовали всю БД.
# Здесь каждая уникальная DDL выполняется один раз за процесс (в любом месте
# кода), повторы заменяются на SELECT 1. Схему владеют миграции - runtime-DDL
# только страхуют, поэтому пропуск повторов безопасен.
# ---------------------------------------------------------------------------
import threading as _threading

from sqlalchemy import event as _event

_DDL_ONCE: set = set()
_DDL_PENDING: set = set()
_DDL_LOCK = _threading.Lock()


def _ddl_key(statement: str):
    u = " ".join(statement.lstrip().upper().split())
    if "IF NOT EXISTS" not in u:
        return None
    if u.startswith(("ALTER TABLE", "CREATE TABLE", "CREATE INDEX", "CREATE UNIQUE INDEX")):
        return u
    return None


@_event.listens_for(engine, "before_cursor_execute", retval=True)
def _ddl_once_before(conn, cursor, statement, parameters, context, executemany):
    if executemany:
        return statement, parameters
    key = _ddl_key(statement)
    if key is None:
        return statement, parameters
    with _DDL_LOCK:
        if key in _DDL_ONCE:
            return "SELECT 1", ()
        _DDL_PENDING.add(key)
    return statement, parameters


@_event.listens_for(engine, "after_cursor_execute")
def _ddl_once_after(conn, cursor, statement, parameters, context, executemany):
    key = _ddl_key(statement)
    if key is None:
        return
    with _DDL_LOCK:
        if key in _DDL_PENDING:
            _DDL_PENDING.discard(key)
            _DDL_ONCE.add(key)
