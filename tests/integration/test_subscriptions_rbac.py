# tests/integration/test_subscriptions_rbac.py

# импорт os для переменных окружения
import os

# импорт uuid для случайных значений
import uuid

# импорт date
from datetime import date

# импорт requests
import requests


# базовый адрес API
BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# токены ролей
MANAGER_TOKEN = os.getenv("TEST_MANAGER_TOKEN", "")
TRAINER_TOKEN = os.getenv("TEST_TRAINER_TOKEN", "")
CASHIER_TOKEN = os.getenv("TEST_CASHIER_TOKEN", "")
SUPPORT_TOKEN = os.getenv("TEST_SUPPORT_TOKEN", "")


# заголовки
def build_headers(token: str) -> dict:
    # возвращаем заголовки
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# helper для создания клиента через manager
def create_client_by_manager() -> dict:
    # проверяем токен manager
    assert MANAGER_TOKEN, "Не задан TEST_MANAGER_TOKEN"

    # генерируем суффикс
    suffix = uuid.uuid4().hex[:8]
    numeric_suffix = "".join(ch for ch in suffix if ch.isdigit())
    numeric_suffix = (numeric_suffix + "12345678")[:8]

    # создаём клиента
    response = requests.post(
        f"{BASE_URL}/clients/",
        headers=build_headers(MANAGER_TOKEN),
        json={
            "first_name": "RBAC",
            "last_name": f"Subscription_{suffix}",
            "phone": f"+7999{numeric_suffix}",
            "email": f"rbac_subscription_{suffix}@test.com",
            "status": "ACTIVE",
            "is_active": True,
        },
        timeout=15,
    )

    # проверяем ответ
    assert response.status_code == 201, response.text

    # возвращаем клиента
    return response.json()


# helper для создания тарифа через manager
def create_tariff_by_manager() -> dict:
    # проверяем токен manager
    assert MANAGER_TOKEN, "Не задан TEST_MANAGER_TOKEN"

    # создаём суффикс
    suffix = uuid.uuid4().hex[:8].upper()

    # создаём тариф
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=build_headers(MANAGER_TOKEN),
        json={
            "code": f"RBAC_SUB_{suffix}",
            "name": f"RBAC subscription tariff {suffix}",
            "description": "Проверка прав subscriptions",
            "price": 3000.00,
            "currency": "RUB",
            "duration_days": 30,
            "visit_limit": 8,
            "is_unlimited": False,
            "is_active": True,
        },
        timeout=15,
    )

    # проверяем ответ
    assert response.status_code == 201, response.text

    # возвращаем тариф
    return response.json()


# trainer может читать абонементы
def test_trainer_can_read_subscriptions():
    # проверяем токен
    assert TRAINER_TOKEN, "Не задан TEST_TRAINER_TOKEN"

    # отправляем запрос
    response = requests.get(
        f"{BASE_URL}/subscriptions/",
        headers=build_headers(TRAINER_TOKEN),
        timeout=15,
    )

    # ожидаем успех
    assert response.status_code == 200, response.text


# support может читать абонементы
def test_support_can_read_subscriptions():
    # проверяем токен
    assert SUPPORT_TOKEN, "Не задан TEST_SUPPORT_TOKEN"

    # отправляем запрос
    response = requests.get(
        f"{BASE_URL}/subscriptions/",
        headers=build_headers(SUPPORT_TOKEN),
        timeout=15,
    )

    # ожидаем успех
    assert response.status_code == 200, response.text


# trainer не может создавать абонементы
def test_trainer_cannot_create_subscriptions():
    # проверяем токен
    assert TRAINER_TOKEN, "Не задан TEST_TRAINER_TOKEN"

    # создаём тестовые сущности manager-ом
    client = create_client_by_manager()
    tariff = create_tariff_by_manager()

    # отправляем запрос от trainer
    response = requests.post(
        f"{BASE_URL}/subscriptions/",
        headers=build_headers(TRAINER_TOKEN),
        json={
            "client_id": client["id"],
            "tariff_id": tariff["id"],
            "start_date": str(date.today()),
            "status": "ACTIVE",
            "notes": "Trainer forbidden",
        },
        timeout=15,
    )

    # ожидаем запрет
    assert response.status_code == 403, response.text


# cashier может создавать абонементы
def test_cashier_can_create_subscriptions():
    # проверяем токен
    assert CASHIER_TOKEN, "Не задан TEST_CASHIER_TOKEN"

    # создаём тестовые сущности manager-ом
    client = create_client_by_manager()
    tariff = create_tariff_by_manager()

    # отправляем запрос от cashier
    response = requests.post(
        f"{BASE_URL}/subscriptions/",
        headers=build_headers(CASHIER_TOKEN),
        json={
            "client_id": client["id"],
            "tariff_id": tariff["id"],
            "start_date": str(date.today()),
            "status": "ACTIVE",
            "notes": "Cashier allowed",
        },
        timeout=15,
    )

    # ожидаем успех
    assert response.status_code == 201, response.text