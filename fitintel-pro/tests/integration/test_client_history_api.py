# tests/integration/test_client_history_api.py

import os
import uuid
import requests

BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000/api/v1")
TOKEN = os.getenv("TEST_API_TOKEN", "")


def build_headers() -> dict:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def build_client_payload() -> dict:
    suffix = uuid.uuid4().hex[:8]
    numeric_suffix = "".join(ch for ch in suffix if ch.isdigit())
    numeric_suffix = (numeric_suffix + "12345678")[:8]

    return {
        "first_name": "История",
        "last_name": f"Клиент_{suffix}",
        "phone": f"+7999{numeric_suffix}",
        "email": f"history_client_{suffix}@test.com",
        "gender": "ЖЕНСКИЙ",
        "client_category": "ВЗРОСЛЫЙ",
    }


def test_client_timeline_after_create_and_update():
    assert TOKEN, "TEST_API_TOKEN не задан"

    # создаём клиента
    create_response = requests.post(
        f"{BASE_URL}/clients/",
        headers=build_headers(),
        json=build_client_payload(),
        timeout=15,
    )

    assert create_response.status_code == 201, create_response.text
    client = create_response.json()
    client_id = client["id"]

    # обновляем клиента
    update_response = requests.patch(
        f"{BASE_URL}/clients/{client_id}",
        headers=build_headers(),
        json={"client_category": "VIP"},
        timeout=15,
    )

    assert update_response.status_code == 200, update_response.text

    # получаем timeline
    timeline_response = requests.get(
        f"{BASE_URL}/clients/{client_id}/timeline",
        headers=build_headers(),
        timeout=15,
    )

    assert timeline_response.status_code == 200, timeline_response.text

    data = timeline_response.json()

    assert "items" in data
    assert "count" in data
    assert data["count"] >= 2

    event_types = [item["event_type"] for item in data["items"]]

    assert "КЛИЕНТ_СОЗДАН" in event_types
    assert "КЛИЕНТ_ОБНОВЛЁН" in event_types


def test_client_timeline_pagination():
    assert TOKEN, "TEST_API_TOKEN не задан"

    # создаём клиента
    suffix = uuid.uuid4().hex[:8]
    numeric_suffix = "".join(ch for ch in suffix if ch.isdigit())
    numeric_suffix = (numeric_suffix + "12345678")[:8]

    create_response = requests.post(
        f"{BASE_URL}/clients/",
        headers=build_headers(),
        json={
            "first_name": "Пагинация",
            "last_name": f"Тест_{suffix}",
            "phone": f"+7999{numeric_suffix}",
            "email": f"pagination_{suffix}@test.com",
        },
        timeout=15,
    )

    assert create_response.status_code == 201, create_response.text
    client_id = create_response.json()["id"]

    # обновляем клиента несколько раз
    for i in range(3):
        update_response = requests.patch(
            f"{BASE_URL}/clients/{client_id}",
            headers=build_headers(),
            json={"first_name": f"Обновление_{i}"},
            timeout=15,
        )
        assert update_response.status_code == 200, update_response.text

    # проверяем пагинацию с limit=2
    timeline_response = requests.get(
        f"{BASE_URL}/clients/{client_id}/timeline?limit=2",
        headers=build_headers(),
        timeout=15,
    )

    assert timeline_response.status_code == 200, timeline_response.text
    data = timeline_response.json()

    assert len(data["items"]) == 2
    assert data["count"] >= 4  # создание + 3 обновления