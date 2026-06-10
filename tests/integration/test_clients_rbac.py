# tests/integration/test_clients_rbac.py

# импорт os для чтения переменных окружения
import os

# импорт uuid для уникальных значений
import uuid

# импорт requests для HTTP-запросов
import requests


# базовый адрес API
BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# токены ролей
MANAGER_TOKEN = os.getenv("TEST_MANAGER_TOKEN", "")
TRAINER_TOKEN = os.getenv("TEST_TRAINER_TOKEN", "")
SUPPORT_TOKEN = os.getenv("TEST_SUPPORT_TOKEN", "")


# функция строит заголовки авторизации
def build_headers(token: str) -> dict:
    # возвращаем словарь заголовков
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# helper для создания уникального клиента
def build_client_payload() -> dict:
    # создаём уникальный суффикс
    suffix = uuid.uuid4().hex[:8]

    # собираем цифры для телефона
    numeric_suffix = "".join(ch for ch in suffix if ch.isdigit())
    numeric_suffix = (numeric_suffix + "12345678")[:8]

    # возвращаем payload
    return {
        "first_name": "RBAC",
        "last_name": f"Client_{suffix}",
        "phone": f"+7999{numeric_suffix}",
        "email": f"rbac_client_{suffix}@test.com",
        "status": "ACTIVE",
        "is_active": True,
    }


# trainer может читать клиентов
def test_trainer_can_read_clients():
    # проверяем наличие токена
    assert TRAINER_TOKEN, "Не задан TEST_TRAINER_TOKEN"

    # отправляем запрос
    response = requests.get(
        f"{BASE_URL}/clients/",
        headers=build_headers(TRAINER_TOKEN),
        timeout=15,
    )

    # ожидаем успех
    assert response.status_code == 200, response.text


# trainer не может создавать клиентов
def test_trainer_cannot_create_client():
    # проверяем наличие токена
    assert TRAINER_TOKEN, "Не задан TEST_TRAINER_TOKEN"

    # создаём payload
    payload = build_client_payload()

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/clients/",
        headers=build_headers(TRAINER_TOKEN),
        json=payload,
        timeout=15,
    )

    # ожидаем запрет
    assert response.status_code == 403, response.text


# manager может создавать клиентов
def test_manager_can_create_client():
    # проверяем наличие токена
    assert MANAGER_TOKEN, "Не задан TEST_MANAGER_TOKEN"

    # создаём payload
    payload = build_client_payload()

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/clients/",
        headers=build_headers(MANAGER_TOKEN),
        json=payload,
        timeout=15,
    )

    # ожидаем успешное создание
    assert response.status_code == 201, response.text


# support не может создавать клиентов
def test_support_cannot_create_client():
    # проверяем наличие токена
    assert SUPPORT_TOKEN, "Не задан TEST_SUPPORT_TOKEN"

    # создаём payload
    payload = build_client_payload()

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/clients/",
        headers=build_headers(SUPPORT_TOKEN),
        json=payload,
        timeout=15,
    )

    # ожидаем запрет
    assert response.status_code == 403, response.text