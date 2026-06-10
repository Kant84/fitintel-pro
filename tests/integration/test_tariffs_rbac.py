# tests/integration/test_tariffs_rbac.py

# импорт os для переменных окружения
import os

# импорт uuid для уникальных кодов
import uuid

# импорт requests для HTTP-запросов
import requests


# базовый адрес API
BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# токены ролей
MANAGER_TOKEN = os.getenv("TEST_MANAGER_TOKEN", "")
TRAINER_TOKEN = os.getenv("TEST_TRAINER_TOKEN", "")
CASHIER_TOKEN = os.getenv("TEST_CASHIER_TOKEN", "")


# функция строит заголовки
def build_headers(token: str) -> dict:
    # возвращаем заголовки
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# helper для payload тарифа
def build_tariff_payload() -> dict:
    # создаём уникальный суффикс
    suffix = uuid.uuid4().hex[:8].upper()

    # возвращаем payload
    return {
        "code": f"RBAC_{suffix}",
        "name": f"RBAC тариф {suffix}",
        "description": "Проверка RBAC для тарифов",
        "price": 2500.00,
        "currency": "RUB",
        "duration_days": 30,
        "visit_limit": 8,
        "is_unlimited": False,
        "is_active": True,
    }


# trainer может читать тарифы
def test_trainer_can_read_tariffs():
    # проверяем токен
    assert TRAINER_TOKEN, "Не задан TEST_TRAINER_TOKEN"

    # отправляем запрос
    response = requests.get(
        f"{BASE_URL}/tariffs/",
        headers=build_headers(TRAINER_TOKEN),
        timeout=15,
    )

    # ожидаем успех
    assert response.status_code == 200, response.text


# trainer не может создавать тарифы
def test_trainer_cannot_create_tariff():
    # проверяем токен
    assert TRAINER_TOKEN, "Не задан TEST_TRAINER_TOKEN"

    # создаём payload
    payload = build_tariff_payload()

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=build_headers(TRAINER_TOKEN),
        json=payload,
        timeout=15,
    )

    # ожидаем запрет
    assert response.status_code == 403, response.text


# manager может создавать тарифы
def test_manager_can_create_tariff():
    # проверяем токен
    assert MANAGER_TOKEN, "Не задан TEST_MANAGER_TOKEN"

    # создаём payload
    payload = build_tariff_payload()

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=build_headers(MANAGER_TOKEN),
        json=payload,
        timeout=15,
    )

    # ожидаем успех
    assert response.status_code == 201, response.text


# cashier не может создавать тарифы
def test_cashier_cannot_create_tariff():
    # проверяем токен
    assert CASHIER_TOKEN, "Не задан TEST_CASHIER_TOKEN"

    # создаём payload
    payload = build_tariff_payload()

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=build_headers(CASHIER_TOKEN),
        json=payload,
        timeout=15,
    )

    # ожидаем запрет
    assert response.status_code == 403, response.text