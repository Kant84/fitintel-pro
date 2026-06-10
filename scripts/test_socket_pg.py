# scripts/test_socket_pg.py

# импорт модуля sys для добавления корня проекта в путь импорта
import sys

# импорт pathlib для работы с путями
from pathlib import Path

# добавляем корень проекта в sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# импорт модуля socket для прямой TCP-проверки
import socket

# импорт настроек проекта
from app.core.config import settings


# печатаем адрес проверки
print("=== SOCKET TEST ===")
print("HOST =", settings.POSTGRES_HOST)
print("PORT =", settings.POSTGRES_PORT)
print()

try:
    # пытаемся открыть TCP-соединение с PostgreSQL
    with socket.create_connection(
        (settings.POSTGRES_HOST, settings.POSTGRES_PORT),
        timeout=5,
    ) as sock:
        print("SOCKET TEST OK")
        print("peer =", sock.getpeername())
except Exception as exc:
    print("SOCKET TEST ERROR:", repr(exc))