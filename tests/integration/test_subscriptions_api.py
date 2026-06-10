# tests/integration/test_subscriptions_api.py

import os
import uuid
from datetime import date

import pytest
import requests


BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000/api/v1")
TOKEN = os.getenv("TEST_API_TOKEN", "")
USER_ID = os.getenv("TEST_USER_ID", "")


@pytest.fixture(scope="session")
def auth_headers():
    assert TOKEN, "Не задан TEST_API_TOKEN"

    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.fixture(scope="session")
def test_user_id():
    assert USER_ID, "Не задан TEST_USER_ID"
    return USER_ID


def create_client(auth_headers):
    suffix = uuid.uuid4().hex[:8]
    numeric_suffix = "".join(ch for ch in suffix if ch.isdigit())
    numeric_suffix = (numeric_suffix + "12345678")[:8]

    payload = {
        "first_name": "Иван",
        "last_name": f"Подписка_{suffix}",
        "phone": f"+7999{numeric_suffix}",
        "email": f"subscription_{suffix}@test.com",
        "status": "ACTIVE",
        "is_active": True,
    }

    response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_tariff(auth_headers):
    suffix = uuid.uuid4().hex[:8].upper()

    payload = {
        "code": f"SUB_TARIFF_{suffix}",
        "name": f"Тариф подписки {suffix}",
        "description": f"Тариф для теста {suffix}",
        "price": 4500.00,
        "currency": "RUB",
        "duration_days": 30,
        "visit_limit": 8,
        "is_unlimited": False,
        "is_active": True,
    }

    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_get_user_permissions(auth_headers, test_user_id):
    response = requests.get(
        f"{BASE_URL}/users/{test_user_id}/permissions",
        headers=auth_headers,
        timeout=15,
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert "user_id" in data
    assert "permissions" in data
    assert isinstance(data["permissions"], list)


def test_list_subscriptions(auth_headers):
    response = requests.get(
        f"{BASE_URL}/subscriptions/",
        headers=auth_headers,
        params={"offset": 0, "limit": 100},
        timeout=15,
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["count"], int)


def test_create_get_update_subscription(auth_headers):
    client = create_client(auth_headers)
    tariff = create_tariff(auth_headers)

    create_payload = {
        "client_id": client["id"],
        "tariff_id": tariff["id"],
        "start_date": str(date.today()),
        "status": "ACTIVE",
        "notes": "Первичная продажа",
    }

    create_response = requests.post(
        f"{BASE_URL}/subscriptions/",
        headers=auth_headers,
        json=create_payload,
        timeout=15,
    )
    assert create_response.status_code == 201, create_response.text

    created_subscription = create_response.json()
    subscription_id = created_subscription["id"]

    assert created_subscription["client_id"] == client["id"]
    assert created_subscription["tariff_id"] == tariff["id"]
    assert created_subscription["status"] == "ACTIVE"
    assert created_subscription["is_active"] is True
    assert created_subscription["visits_used"] == 0

    get_response = requests.get(
        f"{BASE_URL}/subscriptions/{subscription_id}",
        headers=auth_headers,
        timeout=15,
    )
    assert get_response.status_code == 200, get_response.text

    fetched_subscription = get_response.json()
    assert fetched_subscription["id"] == subscription_id

    update_payload = {
        "visits_used": 8,
        "notes": "Лимит исчерпан",
    }

    update_response = requests.patch(
        f"{BASE_URL}/subscriptions/{subscription_id}",
        headers=auth_headers,
        json=update_payload,
        timeout=15,
    )
    assert update_response.status_code == 200, update_response.text

    updated_subscription = update_response.json()
    assert updated_subscription["visits_used"] == 8
    assert updated_subscription["status"] == "EXPIRED"
    assert updated_subscription["is_active"] is False


def test_create_subscription_invalid_status(auth_headers):
    client = create_client(auth_headers)
    tariff = create_tariff(auth_headers)

    payload = {
        "client_id": client["id"],
        "tariff_id": tariff["id"],
        "start_date": str(date.today()),
        "status": "UNKNOWN_STATUS",
        "notes": "Некорректный статус",
    }

    response = requests.post(
        f"{BASE_URL}/subscriptions/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )
    assert response.status_code == 400, response.text
    assert "статус" in response.text.lower()


def test_create_subscription_client_not_found(auth_headers):
    tariff = create_tariff(auth_headers)

    payload = {
        "client_id": str(uuid.uuid4()),
        "tariff_id": tariff["id"],
        "start_date": str(date.today()),
        "status": "ACTIVE",
        "notes": "Несуществующий клиент",
    }

    response = requests.post(
        f"{BASE_URL}/subscriptions/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )
    assert response.status_code == 404, response.text
    assert "клиент" in response.text.lower()


def test_create_subscription_tariff_not_found(auth_headers):
    client = create_client(auth_headers)

    payload = {
        "client_id": client["id"],
        "tariff_id": str(uuid.uuid4()),
        "start_date": str(date.today()),
        "status": "ACTIVE",
        "notes": "Несуществующий тариф",
    }

    response = requests.post(
        f"{BASE_URL}/subscriptions/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )
    assert response.status_code == 404, response.text
    assert "тариф" in response.text.lower()


def test_update_subscription_invalid_visits_used(auth_headers):
    client = create_client(auth_headers)
    tariff = create_tariff(auth_headers)

    create_payload = {
        "client_id": client["id"],
        "tariff_id": tariff["id"],
        "start_date": str(date.today()),
        "status": "ACTIVE",
        "notes": "Тест отрицательных посещений",
    }

    create_response = requests.post(
        f"{BASE_URL}/subscriptions/",
        headers=auth_headers,
        json=create_payload,
        timeout=15,
    )
    assert create_response.status_code == 201, create_response.text

    subscription_id = create_response.json()["id"]

    update_payload = {
        "visits_used": -1,
    }

    update_response = requests.patch(
        f"{BASE_URL}/subscriptions/{subscription_id}",
        headers=auth_headers,
        json=update_payload,
        timeout=15,
    )
    assert update_response.status_code == 400, update_response.text
    assert "visits_used" in update_response.text.lower()