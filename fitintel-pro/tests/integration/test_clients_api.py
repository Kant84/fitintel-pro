# tests/integration/test_clients_api.py
# tests/integration/test_clients_api.py

# импорт os для чтения переменных окружения
import os

# импорт uuid для генерации уникальных значений
import uuid

# импорт pytest для запуска тестов
import pytest

# импорт requests для HTTP-запросов к API
import requests


# базовый адрес API
BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# токен доступа
TOKEN = os.getenv("TEST_API_TOKEN", "")

# user_id текущего пользователя
USER_ID = os.getenv("TEST_USER_ID", "")


# фикстура формирует заголовки авторизации
@pytest.fixture(scope="session")
def auth_headers():
    # проверяем, что токен передан
    assert TOKEN, "Не задан TEST_API_TOKEN"

    # защита от случайной заглушки
    assert "ТВОЙ_" not in TOKEN, "В TEST_API_TOKEN стоит заглушка, а не реальный токен"

    # возвращаем заголовки
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# фикстура возвращает user_id
@pytest.fixture(scope="session")
def test_user_id():
    # проверяем, что user_id передан
    assert USER_ID, "Не задан TEST_USER_ID"

    # возвращаем user_id
    return USER_ID


# функция создаёт уникальный payload клиента
def build_unique_client_payload():
    # создаём короткий случайный суффикс
    suffix = uuid.uuid4().hex[:8]

    # выделяем из него только цифры
    numeric_suffix = "".join(ch for ch in suffix if ch.isdigit())

    # если цифр мало — дополняем строку
    numeric_suffix = (numeric_suffix + "12345678")[:8]

    # возвращаем уникальный payload
    return {
        "first_name": "Иван",
        "last_name": f"Петров_{suffix}",
        "phone": f"+7999{numeric_suffix}",
        "email": f"ivan_{suffix}@test.com",
        "status": "ACTIVE",
        "is_active": True,
    }


# тест получения прав пользователя
def test_get_user_permissions(auth_headers, test_user_id):
    # отправляем GET-запрос
    response = requests.get(
        f"{BASE_URL}/users/{test_user_id}/permissions",
        headers=auth_headers,
        timeout=15,
    )

    # проверяем код ответа
    assert response.status_code == 200, response.text

    # разбираем JSON
    data = response.json()

    # проверяем поля ответа
    assert "user_id" in data
    assert "permissions" in data
    assert isinstance(data["permissions"], list)


# тест списка клиентов
def test_list_clients(auth_headers):
    # отправляем запрос на список клиентов
    response = requests.get(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        params={
            "offset": 0,
            "limit": 100,
        },
        timeout=15,
    )

    # проверяем код ответа
    assert response.status_code == 200, response.text

    # разбираем JSON
    data = response.json()

    # проверяем структуру
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["count"], int)


# тест create + get + update
def test_create_get_update_client(auth_headers):
    # создаём уникальный payload
    create_payload = build_unique_client_payload()

    # создаём клиента
    create_response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=create_payload,
        timeout=15,
    )

    # проверяем успешное создание
    assert create_response.status_code == 201, create_response.text

    # разбираем ответ
    created_client = create_response.json()

    # проверяем, что id есть
    assert "id" in created_client

    # сохраняем id клиента
    client_id = created_client["id"]

    # проверяем основные поля
    assert created_client["first_name"] == create_payload["first_name"]
    assert created_client["status"] == "ACTIVE"
    assert created_client["is_active"] is True

    # читаем клиента по id
    get_response = requests.get(
        f"{BASE_URL}/clients/{client_id}",
        headers=auth_headers,
        timeout=15,
    )

    # проверяем успешное чтение
    assert get_response.status_code == 200, get_response.text

    # разбираем ответ
    fetched_client = get_response.json()

    # проверяем совпадение id
    assert fetched_client["id"] == client_id

    # проверяем совпадение email
    assert fetched_client["email"] == create_payload["email"]

    # готовим обновление клиента
    update_payload = {
        "first_name": "Пётр",
        "status": "BLOCKED",
    }

    # обновляем клиента
    update_response = requests.patch(
        f"{BASE_URL}/clients/{client_id}",
        headers=auth_headers,
        json=update_payload,
        timeout=15,
    )

    # проверяем успешное обновление
    assert update_response.status_code == 200, update_response.text

    # разбираем ответ
    updated_client = update_response.json()

    # проверяем новое имя
    assert updated_client["first_name"] == "Пётр"

    # проверяем статус
    assert updated_client["status"] == "BLOCKED"

    # проверяем, что клиент стал неактивен
    assert updated_client["is_active"] is False


# тест на дубль email
def test_create_client_duplicate_email(auth_headers):
    # создаём первого клиента
    first_payload = build_unique_client_payload()

    # отправляем запрос на создание
    first_response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=first_payload,
        timeout=15,
    )

    # проверяем, что первый клиент создался
    assert first_response.status_code == 201, first_response.text

    # создаём второй payload
    second_payload = build_unique_client_payload()

    # подменяем email на занятый
    second_payload["email"] = first_payload["email"]

    # отправляем второй запрос
    second_response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=second_payload,
        timeout=15,
    )

    # ждём конфликт
    assert second_response.status_code == 409, second_response.text

    # проверяем текст ошибки
    assert "email" in second_response.text.lower()


# тест на дубль телефона
def test_create_client_duplicate_phone(auth_headers):
    # создаём первого клиента
    first_payload = build_unique_client_payload()

    # отправляем запрос на создание
    first_response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=first_payload,
        timeout=15,
    )

    # проверяем, что первый клиент создался
    assert first_response.status_code == 201, first_response.text

    # создаём второй payload
    second_payload = build_unique_client_payload()

    # подменяем телефон на занятый
    second_payload["phone"] = first_payload["phone"]

    # отправляем второй запрос
    second_response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=second_payload,
        timeout=15,
    )

    # проверяем конфликт
    assert second_response.status_code == 409, second_response.text

    # проверяем текст ошибки
    assert "телефон" in second_response.text.lower() or "phone" in second_response.text.lower()


# тест на неверный статус
def test_create_client_invalid_status(auth_headers):
    # создаём payload
    payload = build_unique_client_payload()

    # передаём неверный статус
    payload["status"] = "string"

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )

    # ожидаем ошибку 400
    assert response.status_code == 400, response.text

    # проверяем, что ошибка про статус
    assert "статус" in response.text.lower()


# тест на неверный телефон
def test_create_client_invalid_phone(auth_headers):
    # создаём payload
    payload = build_unique_client_payload()

    # передаём плохой телефон
    payload["phone"] = "123"

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/clients/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )

    # ожидаем ошибку 422, потому что phone слишком короткий для схемы
    assert response.status_code == 422, response.text

    # проверяем, что ошибка относится к полю phone
    assert "phone" in response.text.lower()