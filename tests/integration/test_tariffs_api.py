# tests/integration/test_tariffs_api.py

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

    # дополнительная защита от случайной заглушки
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


# функция строит уникальный payload тарифа
def build_unique_tariff_payload():
    # создаём случайный короткий суффикс
    suffix = uuid.uuid4().hex[:8].upper()

    # возвращаем уникальный payload
    return {
        "code": f"TARIFF_{suffix}",
        "name": f"Тариф {suffix}",
        "description": f"Описание тарифа {suffix}",
        "price": 3500.00,
        "currency": "RUB",
        "duration_days": 30,
        "visit_limit": 8,
        "is_unlimited": False,
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

    # проверяем структуру ответа
    assert "user_id" in data
    assert "permissions" in data
    assert isinstance(data["permissions"], list)


# тест списка тарифов
def test_list_tariffs(auth_headers):
    # отправляем GET-запрос на список тарифов
    response = requests.get(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        params={
            "offset": 0,
            "limit": 100,
        },
        timeout=15,
    )

    # проверяем успешный ответ
    assert response.status_code == 200, response.text

    # разбираем JSON
    data = response.json()

    # проверяем структуру ответа
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["count"], int)


# тест create + get + update тарифа
def test_create_get_update_tariff(auth_headers):
    # создаём payload нового тарифа
    create_payload = build_unique_tariff_payload()

    # создаём тариф
    create_response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=create_payload,
        timeout=15,
    )

    # проверяем, что тариф успешно создан
    assert create_response.status_code == 201, create_response.text

    # разбираем JSON-ответ
    created_tariff = create_response.json()

    # проверяем наличие id
    assert "id" in created_tariff

    # сохраняем id тарифа
    tariff_id = created_tariff["id"]

    # проверяем основные поля
    assert created_tariff["code"] == create_payload["code"]
    assert created_tariff["name"] == create_payload["name"]
    assert created_tariff["currency"] == "RUB"
    assert created_tariff["is_unlimited"] is False
    assert created_tariff["visit_limit"] == 8

    # получаем тариф по id
    get_response = requests.get(
        f"{BASE_URL}/tariffs/{tariff_id}",
        headers=auth_headers,
        timeout=15,
    )

    # проверяем успешное чтение
    assert get_response.status_code == 200, get_response.text

    # разбираем JSON
    fetched_tariff = get_response.json()

    # проверяем совпадение id
    assert fetched_tariff["id"] == tariff_id

    # готовим обновление
    update_payload = {
        "name": f"{create_payload['name']} ОБНОВЛЁН",
        "price": 4200.00,
        "is_unlimited": True,
        "visit_limit": None,
    }

    # обновляем тариф
    update_response = requests.patch(
        f"{BASE_URL}/tariffs/{tariff_id}",
        headers=auth_headers,
        json=update_payload,
        timeout=15,
    )

    # проверяем успешное обновление
    assert update_response.status_code == 200, update_response.text

    # разбираем JSON
    updated_tariff = update_response.json()

    # проверяем изменённые поля
    assert updated_tariff["name"] == update_payload["name"]
    assert str(updated_tariff["price"]) == "4200.00"
    assert updated_tariff["is_unlimited"] is True
    assert updated_tariff["visit_limit"] is None


# тест дубля code
def test_create_tariff_duplicate_code(auth_headers):
    # создаём первый тариф
    first_payload = build_unique_tariff_payload()

    # отправляем запрос на создание первого тарифа
    first_response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=first_payload,
        timeout=15,
    )

    # проверяем успешное создание
    assert first_response.status_code == 201, first_response.text

    # создаём второй payload
    second_payload = build_unique_tariff_payload()

    # подменяем code на уже занятый
    second_payload["code"] = first_payload["code"]

    # отправляем второй запрос
    second_response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=second_payload,
        timeout=15,
    )

    # ожидаем конфликт
    assert second_response.status_code == 409, second_response.text

    # проверяем текст ошибки
    assert "code" in second_response.text.lower()


# тест дубля name
def test_create_tariff_duplicate_name(auth_headers):
    # создаём первый тариф
    first_payload = build_unique_tariff_payload()

    # отправляем запрос
    first_response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=first_payload,
        timeout=15,
    )

    # проверяем успешное создание
    assert first_response.status_code == 201, first_response.text

    # создаём второй payload
    second_payload = build_unique_tariff_payload()

    # подменяем name на уже занятый
    second_payload["name"] = first_payload["name"]

    # отправляем второй запрос
    second_response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=second_payload,
        timeout=15,
    )

    # ожидаем конфликт
    assert second_response.status_code == 409, second_response.text

    # проверяем текст ошибки
    assert "name" in second_response.text.lower()


# тест неверной валюты
def test_create_tariff_invalid_currency(auth_headers):
    # создаём payload
    payload = build_unique_tariff_payload()

    # задаём неверную валюту
    payload["currency"] = "USD"

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )

    # ожидаем 400
    assert response.status_code == 400, response.text

    # проверяем текст ошибки
    assert "валюта" in response.text.lower() or "currency" in response.text.lower()


# тест неверной логики visit_limit
def test_create_tariff_invalid_visit_logic(auth_headers):
    # создаём payload
    payload = build_unique_tariff_payload()

    # делаем тариф не безлимитным, но не передаём visit_limit
    payload["is_unlimited"] = False
    payload["visit_limit"] = None

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )

    # ожидаем ошибку 400
    assert response.status_code == 400, response.text

    # проверяем текст ошибки
    assert "visit_limit" in response.text.lower()


# тест неверной цены
def test_create_tariff_invalid_price(auth_headers):
    # создаём payload
    payload = build_unique_tariff_payload()

    # задаём неверную цену
    payload["price"] = 0

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )

    # ожидаем ошибку 400
    assert response.status_code == 400, response.text

    # проверяем текст ошибки
    assert "цена" in response.text.lower() or "price" in response.text.lower()


# тест неверной длительности
def test_create_tariff_invalid_duration(auth_headers):
    # создаём payload
    payload = build_unique_tariff_payload()

    # задаём неверную длительность
    payload["duration_days"] = 0

    # отправляем запрос
    response = requests.post(
        f"{BASE_URL}/tariffs/",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )

    # ожидаем ошибку 400
    assert response.status_code == 400, response.text

    # проверяем текст ошибки
    assert "срок" in response.text.lower() or "duration" in response.text.lower()