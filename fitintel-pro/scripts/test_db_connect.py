# scripts/test_db_connect.py

# импорт psycopg для прямого подключения к PostgreSQL
import psycopg

# импорт text и create_engine из SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# импорт настроек проекта
from app.core.config import settings


# печатаем реальные настройки подключения
print("=== SETTINGS ===")
print("POSTGRES_HOST =", settings.POSTGRES_HOST)
print("POSTGRES_PORT =", settings.POSTGRES_PORT)
print("POSTGRES_DB   =", settings.POSTGRES_DB)
print("POSTGRES_USER =", settings.POSTGRES_USER)
print("DATABASE_URL  =", settings.DATABASE_URL)
print()


# ----------------------------------------------------------
# 1. Проверка через чистый psycopg без DSN-строки
# ----------------------------------------------------------
print("=== TEST 1: psycopg.connect(...) with explicit params ===")

try:
    with psycopg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        connect_timeout=5,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1;")
            row = cur.fetchone()
            print("TEST 1 OK:", row)
except Exception as exc:
    print("TEST 1 ERROR:", repr(exc))

print()


# ----------------------------------------------------------
# 2. Проверка через SQLAlchemy URL.create()
# ----------------------------------------------------------
print("=== TEST 2: SQLAlchemy create_engine(URL.create(...)) ===")

try:
    db_url = URL.create(
        drivername="postgresql+psycopg",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
    )

    print("SQLALCHEMY URL =", db_url)

    engine = create_engine(
        db_url,
        echo=True,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

    with engine.connect() as conn:
        result = conn.execute(text("select 1")).scalar()
        print("TEST 2 OK:", result)

except Exception as exc:
    print("TEST 2 ERROR:", repr(exc))

print()