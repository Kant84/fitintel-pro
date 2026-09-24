# scripts/bootstrap_db.py — первичная инициализация БД
# create_all создаёт все таблицы по моделям, stamp помечает миграции как применённые.
# После этого новые миграции применяются обычным "alembic upgrade head".
import os
import subprocess
import sys

from sqlalchemy import create_engine

from app.db.base import Base
import app.models  # noqa: F401 — регистрация всех моделей в metadata

url = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', '5432')}"
    f"/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(url)
Base.metadata.create_all(engine)
print("OK: таблицы созданы")

subprocess.run([sys.executable, "-m", "alembic", "stamp", "head"], check=True)
print("OK: миграции зафиксированы (stamp head)")
