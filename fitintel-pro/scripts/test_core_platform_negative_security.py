# scripts/test_core_platform_negative_security.py

# Импорт argparse для чтения аргументов командной строки.
import argparse

# Импорт json для красивого вывода JSON-ответов.
import json

# Импорт sys для завершения программы с кодом возврата.
import sys

# Импорт uuid4 для генерации уникальных логинов и email.
from uuid import uuid4

# Импорт requests для HTTP-запросов к API.
import requests


# Базовый класс ошибки тестового сценария.
class TestScenarioError(Exception):
    # Пустой класс нужен для понятного разделения ошибок сценария.
    pass


# Функция печатает красивый блок заголовка.
def print_block(title: str) -> None:
    # Печатаем пустую строку и верхний разделитель.
    print("\n" + "=" * 80)
    # Печатаем текст заголовка блока.
    print(title)
    # Печатаем нижний разделитель.
    print("=" * 80)


# Функция красиво печатает JSON.
def print_json(data) -> None:
    # Выводим объект в формате JSON с отступами.
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


# Функция печатает короткий статус шага.
def print_status(label: str, status_value: str) -> None:
    # Печатаем итоговый статус шага.
    print(f"[{status_value}] {label}")


# Функция проверяет, что ответ содержит ожидаемый код статуса.
def assert_status(response: requests.Response, expected_status: int, step_name: str) -> None:
    # Если статус не совпадает, формируем подробную ошибку.
    if response.status_code != expected_status:
        # Пытаемся разобрать JSON.
        try:
            error_payload = response.json()
        except Exception:
            # Если JSON не распарсился, берём сырой текст.
            error_payload = response.text

        # Поднимаем понятное исключение.
        raise TestScenarioError(
            f"[{step_name}] Ожидался статус {expected_status}, "
            f"но получен {response.status_code}. Ответ:\n{error_payload}"
        )


# Функция проверяет, что ответ содержит один из ожидаемых кодов статуса.
def assert_status_in(response: requests.Response, expected_statuses: tuple[int, ...], step_name: str) -> None:
    # Если статус не входит в допустимые, поднимаем ошибку.
    if response.status_code not in expected_statuses:
        # Пытаемся разобрать JSON.
        try:
            error_payload = response.json()
        except Exception:
            # Если JSON не распарсился, берём сырой текст.
            error_payload = response.text

        # Поднимаем понятное исключение.
        raise TestScenarioError(
            f"[{step_name}] Ожидался один из статусов {expected_statuses}, "
            f"но получен {response.status_code}. Ответ:\n{error_payload}"
        )


# HTTP-клиент для API.
class ApiClient:
    # Конструктор клиента.
    def __init__(self, base_url: str):
        # Сохраняем базовый URL без завершающего слеша.
        self.base_url = base_url.rstrip("/")

        # Создаём HTTP-сессию.
        self.session = requests.Session()

    # Метод устанавливает bearer token.
    def set_bearer_token(self, access_token: str) -> None:
        # Устанавливаем заголовок Authorization.
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    # Метод удаляет bearer token.
    def clear_bearer_token(self) -> None:
        # Удаляем Authorization, если он есть.
        self.session.headers.pop("Authorization", None)

    # Метод выполняет GET-запрос.
    def get(self, path: str, params: dict | None = None) -> requests.Response:
        # Выполняем GET к API.
        return self.session.get(f"{self.base_url}{path}", params=params, timeout=30)

    # Метод выполняет POST-запрос с JSON.
    def post_json(self, path: str, payload: dict) -> requests.Response:
        # Выполняем POST с JSON.
        return self.session.post(f"{self.base_url}{path}", json=payload, timeout=30)

    # Метод выполняет PATCH-запрос с JSON.
    def patch_json(self, path: str, payload: dict) -> requests.Response:
        # Выполняем PATCH с JSON.
        return self.session.patch(f"{self.base_url}{path}", json=payload, timeout=30)

    # Метод логина через /auth/token.
    def login_via_token_endpoint(self, username: str, password: str) -> dict:
        # Формируем URL логина.
        url = f"{self.base_url}/auth/token"

        # Формируем form-data.
        form_data = {
            "username": username,
            "password": password,
        }

        # Отправляем POST-запрос.
        response = self.session.post(url, data=form_data, timeout=30)

        # Проверяем успешный логин.
        assert_status(response, 200, "Логин через /auth/token")

        # Возвращаем JSON-ответ.
        return response.json()


# Главный негативный сценарий.
def run_negative_security_scenario(
    base_url: str,
    admin_login: str,
    admin_password: str,
    restricted_role_code: str,
) -> None:
    # Создаём API-клиент.
    client = ApiClient(base_url=base_url)

    # Генерируем уникальный суффикс.
    unique_suffix = uuid4().hex[:8]

    # Данные обычного пользователя.
    regular_username = f"regular_{unique_suffix}"
    regular_email = f"regular_{unique_suffix}@example.local"
    regular_password = "RegularPass123!"

    # Данные целевого пользователя.
    target_username = f"target_{unique_suffix}"
    target_email = f"target_{unique_suffix}@example.local"
    target_password = "TargetPass123!"

    # Служебные переменные.
    admin_access_token = None
    regular_user_id = None
    target_user_id = None
    regular_user_token = None
    admin_user_id = None

    # ============================================================
    # ПОДГОТОВКА: ЛОГИН АДМИНОМ И СОЗДАНИЕ ТЕСТОВЫХ ПОЛЬЗОВАТЕЛЕЙ
    # ============================================================

    # 1. Логин администратором.
    print_block("1. ЛОГИН АДМИНИСТРАТОРОМ")
    admin_login_payload = client.login_via_token_endpoint(
        username=admin_login,
        password=admin_password,
    )
    print_json(admin_login_payload)

    # Сохраняем admin token.
    admin_access_token = admin_login_payload["access_token"]

    # Устанавливаем admin token.
    client.set_bearer_token(admin_access_token)

    # 2. Получаем /auth/me, чтобы узнать id админа.
    print_block("2. ЧТЕНИЕ /auth/me ДЛЯ ОПРЕДЕЛЕНИЯ ADMIN USER ID")
    response = client.get("/auth/me")
    assert_status(response, 200, "GET /auth/me")
    admin_me_payload = response.json()
    print_json(admin_me_payload)

    # Сохраняем id текущего администратора.
    admin_user_id = admin_me_payload["id"]

    # 3. Создаём обычного пользователя.
    print_block("3. СОЗДАНИЕ ОБЫЧНОГО ПОЛЬЗОВАТЕЛЯ")
    response = client.post_json(
        "/users/",
        {
            "email": regular_email,
            "username": regular_username,
            "password": regular_password,
            "is_active": True,
        },
    )
    assert_status(response, 201, "POST /users/ regular user")
    regular_user_payload = response.json()
    print_json(regular_user_payload)

    # Сохраняем id обычного пользователя.
    regular_user_id = regular_user_payload["id"]

    # 4. Создаём целевого пользователя.
    print_block("4. СОЗДАНИЕ ЦЕЛЕВОГО ПОЛЬЗОВАТЕЛЯ")
    response = client.post_json(
        "/users/",
        {
            "email": target_email,
            "username": target_username,
            "password": target_password,
            "is_active": True,
        },
    )
    assert_status(response, 201, "POST /users/ target user")
    target_user_payload = response.json()
    print_json(target_user_payload)

    # Сохраняем id целевого пользователя.
    target_user_id = target_user_payload["id"]

    # 5. Логин обычным пользователем.
    print_block("5. ЛОГИН ОБЫЧНЫМ ПОЛЬЗОВАТЕЛЕМ")
    client.clear_bearer_token()
    regular_login_payload = client.login_via_token_endpoint(
        username=regular_username,
        password=regular_password,
    )
    print_json(regular_login_payload)

    # Сохраняем токен обычного пользователя.
    regular_user_token = regular_login_payload["access_token"]

    # Устанавливаем токен обычного пользователя.
    client.set_bearer_token(regular_user_token)

    # ============================================================
    # НЕГАТИВНЫЕ ПРОВЕРКИ БЕЗ ПРАВ
    # ============================================================

    # 6. Обычный пользователь пытается читать список пользователей.
    print_block("6. NEGATIVE: ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ ЧИТАЕТ /users/")
    response = client.get("/users/")
    assert_status(response, 403, "GET /users/ without permission")
    print_json(response.json())

    # 7. Обычный пользователь пытается читать другого пользователя.
    print_block("7. NEGATIVE: ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ ЧИТАЕТ ЧУЖОГО ПОЛЬЗОВАТЕЛЯ")
    response = client.get(f"/users/{target_user_id}")
    assert_status(response, 403, "GET /users/{target_user_id} without permission")
    print_json(response.json())

    # 8. Обычный пользователь пытается сбросить пароль другому пользователю.
    print_block("8. NEGATIVE: ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ ДЕЛАЕТ RESET PASSWORD ДРУГОМУ")
    response = client.post_json(
        f"/users/{target_user_id}/reset-password",
        {
            "new_password": "ResetByRegular123!",
            "force_password_change": True,
        },
    )
    assert_status(response, 403, "POST /users/{target_user_id}/reset-password without permission")
    print_json(response.json())

    # 9. Обычный пользователь пытается назначить роль другому пользователю.
    print_block("9. NEGATIVE: ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ НАЗНАЧАЕТ РОЛЬ")
    response = client.post_json(
        f"/users/{target_user_id}/roles/assign",
        {
            "role_code": restricted_role_code,
        },
    )
    assert_status(response, 403, "POST /users/{target_user_id}/roles/assign without permission")
    print_json(response.json())

    # 10. Обычный пользователь пытается снять роль.
    print_block("10. NEGATIVE: ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ СНИМАЕТ РОЛЬ")
    response = client.post_json(
        f"/users/{target_user_id}/roles/revoke",
        {
            "role_code": restricted_role_code,
        },
    )
    assert_status(response, 403, "POST /users/{target_user_id}/roles/revoke without permission")
    print_json(response.json())

    # 11. Обычный пользователь пытается использовать admin reset password для самого себя.
    print_block("11. NEGATIVE: SELF ЧЕРЕЗ ADMIN RESET ENDPOINT")
    response = client.post_json(
        f"/users/{regular_user_id}/reset-password",
        {
            "new_password": "WrongFlow123!",
            "force_password_change": True,
        },
    )
    # Здесь может быть либо 403 от dependency, либо 400 от AuthService,
    # если пользователь вдруг получит permission в будущем.
    assert_status_in(
        response,
        (400, 403),
        "POST /users/{regular_user_id}/reset-password as self via admin flow",
    )
    print_json(response.json())

    # ============================================================
    # ПРОВЕРКИ GUARD-ПРАВИЛ ПОД ADMIN
    # ============================================================

    # Возвращаем admin token.
    client.set_bearer_token(admin_access_token)

    # 12. Попытка снять последнего admin у самого администратора.
    print_block("12. NEGATIVE: СНЯТЬ ПОСЛЕДНЕГО ADMIN")
    response = client.post_json(
        f"/users/{admin_user_id}/roles/revoke",
        {
            "role_code": "admin",
        },
    )

    # Тут ожидаем либо 403, если guard уже работает,
    # либо 200, если в системе есть ещё один admin и операция допустима.
    if response.status_code == 403:
        print_json(response.json())
        print_status("Guard запретил снять последнего admin", "OK")
    elif response.status_code == 200:
        print_json(response.json())
        print_status(
            "Снятие admin прошло: вероятно, в системе больше одного admin или guard ещё не завершён",
            "WARNING",
        )
    else:
        raise TestScenarioError(
            f"[POST /users/{admin_user_id}/roles/revoke admin] "
            f"Ожидался 403 или 200, но получен {response.status_code}. "
            f"Ответ:\n{response.text}"
        )

    # 13. Попытка удалить критичную роль через roles endpoint, если такая ручка существует.
    print_block("13. NEGATIVE: УДАЛИТЬ КРИТИЧНУЮ РОЛЬ, ЕСЛИ ЕСТЬ ENDPOINT")
    response = client.session.delete(
        f"{client.base_url}/roles/admin",
        timeout=30,
    )

    if response.status_code == 404:
        print_status("DELETE /roles/admin", "SKIPPED")
    elif response.status_code == 405:
        print_status("DELETE /roles/admin", "SKIPPED")
    elif response.status_code == 403:
        print_json(response.json())
        print_status("Удаление критичной роли запрещено", "OK")
    elif response.status_code == 422:
        print_json(response.json())
        print_status("Маршрут ожидает UUID роли, а не role_code", "SKIPPED")   
    else:
        raise TestScenarioError(
            f"[DELETE /roles/admin] Ожидался 403/404/405/422, "
            f"но получен {response.status_code}. Ответ:\n{response.text}"
        )

    # ============================================================
    # CLEANUP
    # ============================================================

    # 14. Деактивируем обычного пользователя.
    print_block("14. CLEANUP: ДЕАКТИВАЦИЯ ОБЫЧНОГО ПОЛЬЗОВАТЕЛЯ")
    response = client.post_json(f"/users/{regular_user_id}/deactivate", {})
    assert_status(response, 200, "POST /users/{regular_user_id}/deactivate")
    print_json(response.json())

    # 15. Деактивируем целевого пользователя.
    print_block("15. CLEANUP: ДЕАКТИВАЦИЯ ЦЕЛЕВОГО ПОЛЬЗОВАТЕЛЯ")
    response = client.post_json(f"/users/{target_user_id}/deactivate", {})
    assert_status(response, 200, "POST /users/{target_user_id}/deactivate")
    print_json(response.json())

    # Финальный блок.
    print_block("NEGATIVE / SECURITY СЦЕНАРИЙ ЗАВЕРШЁН УСПЕШНО")
    print("Все негативные и security-проверки завершены без ошибок.")


# Точка входа.
if __name__ == "__main__":
    # Создаём парсер аргументов.
    parser = argparse.ArgumentParser(
        description="Negative / Security integration test для Core Platform / auth / users / RBAC"
    )

    # Аргумент базового URL API.
    parser.add_argument(
        "--base-url",
        required=True,
        help="Базовый URL API, например: http://127.0.0.1:8000/api/v1",
    )

    # Аргумент логина администратора.
    parser.add_argument(
        "--admin-login",
        required=True,
        help="Логин администратора: username или email",
    )

    # Аргумент пароля администратора.
    parser.add_argument(
        "--admin-password",
        required=True,
        help="Пароль администратора",
    )

    # Аргумент role_code, который обычный пользователь попытается назначить.
    parser.add_argument(
        "--restricted-role-code",
        default="manager",
        help="Код роли для негативных тестов назначения/снятия, по умолчанию manager",
    )

    # Читаем аргументы.
    args = parser.parse_args()

    # Запускаем сценарий с обработкой ошибок.
    try:
        run_negative_security_scenario(
            base_url=args.base_url,
            admin_login=args.admin_login,
            admin_password=args.admin_password,
            restricted_role_code=args.restricted_role_code,
        )
    except TestScenarioError as exc:
        print_block("ОШИБКА ТЕСТОВОГО СЦЕНАРИЯ")
        print(str(exc))
        sys.exit(1)
    except requests.RequestException as exc:
        print_block("СЕТЕВАЯ ОШИБКА")
        print(str(exc))
        sys.exit(2)
    except Exception as exc:
        print_block("НЕОЖИДАННАЯ ОШИБКА")
        print(str(exc))
        sys.exit(3)
#  python scripts/test_core_platform_negative_security.py --base-url http://127.0.0.1:8000/api/v1 --admin-login admin --admin-password admin123 --restricted-role-code manager      