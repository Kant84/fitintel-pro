# scripts/test_auth_users_api.py

# Импорт argparse для чтения параметров командной строки.
import argparse

# Импорт json для красивого вывода JSON-ответов.
import json

# Импорт sys для корректного завершения программы с кодом ошибки.
import sys

# Импорт uuid4 для генерации уникального имени тестового пользователя.
from uuid import uuid4

# Импорт requests для HTTP-запросов к FastAPI API.
import requests


# Базовый класс ошибки тестового сценария.
class TestScenarioError(Exception):
    # Внутри класса ничего не нужно, он нужен для читаемого перехвата ошибок.
    pass


# Функция красивого вывода блока в консоль.
def print_block(title: str) -> None:
    # Печатаем визуальный разделитель.
    print("\n" + "=" * 80)
    # Печатаем заголовок блока.
    print(title)
    # Печатаем ещё один визуальный разделитель.
    print("=" * 80)


# Функция красивого вывода JSON.
def print_json(data) -> None:
    # Преобразуем объект Python в красивый JSON-вид.
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


# Вспомогательная функция проверки HTTP-ответа.
def assert_status(response: requests.Response, expected_status: int, step_name: str) -> None:
    # Если код ответа не совпал с ожидаемым — выбрасываем понятную ошибку.
    if response.status_code != expected_status:
        # Пытаемся прочитать JSON-ошибку.
        try:
            error_payload = response.json()
        except Exception:
            error_payload = response.text

        # Формируем подробное сообщение об ошибке.
        raise TestScenarioError(
            f"[{step_name}] Ожидался статус {expected_status}, "
            f"но получен {response.status_code}. Ответ:\n{error_payload}"
        )


# Класс клиента для работы с API.
class ApiClient:
    # Конструктор клиента.
    def __init__(self, base_url: str):
        # Сохраняем базовый URL API без завершающего слеша.
        self.base_url = base_url.rstrip("/")

        # Создаём HTTP-сессию, чтобы переиспользовать соединения.
        self.session = requests.Session()

    # Метод устанавливает bearer token в заголовки.
    def set_bearer_token(self, access_token: str) -> None:
        # Устанавливаем Authorization header для всех последующих запросов.
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    # Метод удаляет bearer token из заголовков.
    def clear_bearer_token(self) -> None:
        # Если заголовок Authorization установлен — удаляем его.
        self.session.headers.pop("Authorization", None)

    # Метод выполняет POST с JSON.
    def post_json(self, path: str, payload: dict) -> requests.Response:
        # Формируем полный URL и отправляем POST-запрос.
        return self.session.post(f"{self.base_url}{path}", json=payload, timeout=30)

    # Метод выполняет PATCH с JSON.
    def patch_json(self, path: str, payload: dict) -> requests.Response:
        # Формируем полный URL и отправляем PATCH-запрос.
        return self.session.patch(f"{self.base_url}{path}", json=payload, timeout=30)

    # Метод выполняет GET.
    def get(self, path: str, params: dict | None = None) -> requests.Response:
        # Формируем полный URL и отправляем GET-запрос.
        return self.session.get(f"{self.base_url}{path}", params=params, timeout=30)

    # Метод логина через OAuth2 form endpoint `/auth/token`.
    def login_via_token_endpoint(self, username: str, password: str) -> dict:
        # Формируем URL логина.
        url = f"{self.base_url}/auth/token"

        # Подготавливаем form-data в формате OAuth2PasswordRequestForm.
        form_data = {
            "username": username,
            "password": password,
        }

        # Отправляем POST-запрос с form-data.
        response = self.session.post(url, data=form_data, timeout=30)

        # Проверяем, что логин успешен.
        assert_status(response, 200, "Логин через /auth/token")

        # Возвращаем JSON-ответ.
        return response.json()


# Главная функция сценария.
def run_scenario(
    base_url: str,
    admin_login: str,
    admin_password: str,
    assign_role_code: str,
) -> None:
    # Создаём API-клиент.
    client = ApiClient(base_url=base_url)

    # Генерируем уникальный суффикс для тестовых сущностей.
    unique_suffix = uuid4().hex[:8]

    # Формируем тестовые данные пользователя.
    test_username = f"test_user_{unique_suffix}"
    test_email = f"test_{unique_suffix}@example.local"
    test_password = "TempPass123!"
    reset_password = "ResetPass123!"
    changed_password = "ChangedPass123!"
    updated_username_by_admin = f"{test_username}_admin"
    updated_username_by_self = f"{test_username}_self"

    # Переменные для промежуточных результатов.
    created_user_id = None
    admin_access_token = None
    test_user_access_token = None

    # 1. Логин администратором.
    print_block("1. ЛОГИН АДМИНИСТРАТОРОМ")
    admin_login_payload = client.login_via_token_endpoint(
        username=admin_login,
        password=admin_password,
    )
    print_json(admin_login_payload)

    # Сохраняем access token администратора.
    admin_access_token = admin_login_payload["access_token"]

    # Устанавливаем токен администратора в заголовки.
    client.set_bearer_token(admin_access_token)

    # 2. Проверка /auth/me.
    print_block("2. ПРОВЕРКА /auth/me")
    response = client.get("/auth/me")
    assert_status(response, 200, "GET /auth/me")
    auth_me_payload = response.json()
    print_json(auth_me_payload)

    # 3. Проверка /users/me.
    print_block("3. ПРОВЕРКА /users/me")
    response = client.get("/users/me")
    assert_status(response, 200, "GET /users/me")
    users_me_payload = response.json()
    print_json(users_me_payload)

    # 4. Создание тестового пользователя.
    print_block("4. СОЗДАНИЕ ТЕСТОВОГО ПОЛЬЗОВАТЕЛЯ")
    create_payload = {
        "email": test_email,
        "username": test_username,
        "password": test_password,
        "is_active": True,
    }
    response = client.post_json("/users/", create_payload)
    assert_status(response, 201, "POST /users/")
    created_user_payload = response.json()
    print_json(created_user_payload)

    # Сохраняем UUID созданного пользователя.
    created_user_id = created_user_payload["id"]

    # 5. Чтение списка пользователей.
    print_block("5. ЧТЕНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ")
    response = client.get("/users/", params={"offset": 0, "limit": 20})
    assert_status(response, 200, "GET /users/")
    users_list_payload = response.json()
    print_json(users_list_payload)

    # 6. Чтение созданного пользователя по UUID.
    print_block("6. ЧТЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО UUID")
    response = client.get(f"/users/{created_user_id}")
    assert_status(response, 200, f"GET /users/{created_user_id}")
    user_by_id_payload = response.json()
    print_json(user_by_id_payload)

    # 7. Обновление пользователя администратором.
    print_block("7. ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ АДМИНИСТРАТОРОМ")
    update_payload = {
        "email": test_email,
        "username": updated_username_by_admin,
        "is_active": True,
    }
    response = client.patch_json(f"/users/{created_user_id}", update_payload)
    assert_status(response, 200, f"PATCH /users/{created_user_id}")
    updated_user_payload = response.json()
    print_json(updated_user_payload)

    # 8. Назначение роли пользователю.
    print_block("8. НАЗНАЧЕНИЕ РОЛИ ПОЛЬЗОВАТЕЛЮ")
    assign_role_payload = {
        "role_code": assign_role_code,
    }
    response = client.post_json(f"/users/{created_user_id}/roles/assign", assign_role_payload)
    assert_status(response, 200, f"POST /users/{created_user_id}/roles/assign")
    assigned_role_payload = response.json()
    print_json(assigned_role_payload)

    # 9. Чтение ролей пользователя.
    print_block("9. ЧТЕНИЕ РОЛЕЙ ПОЛЬЗОВАТЕЛЯ")
    response = client.get(f"/users/{created_user_id}/roles")
    assert_status(response, 200, f"GET /users/{created_user_id}/roles")
    roles_payload = response.json()
    print_json(roles_payload)

    # 10. Чтение permissions пользователя.
    print_block("10. ЧТЕНИЕ PERMISSIONS ПОЛЬЗОВАТЕЛЯ")
    response = client.get(f"/users/{created_user_id}/permissions")
    assert_status(response, 200, f"GET /users/{created_user_id}/permissions")
    permissions_payload = response.json()
    print_json(permissions_payload)

    # 11. Административный сброс пароля пользователя.
    print_block("11. АДМИНИСТРАТИВНЫЙ СБРОС ПАРОЛЯ")
    reset_password_payload = {
        "new_password": reset_password,
        "force_password_change": True,
    }
    response = client.post_json(f"/users/{created_user_id}/reset-password", reset_password_payload)
    assert_status(response, 200, f"POST /users/{created_user_id}/reset-password")
    reset_password_response_payload = response.json()
    print_json(reset_password_response_payload)

    # 12. Логин тестовым пользователем с новым паролем после admin reset.
    print_block("12. ЛОГИН ТЕСТОВЫМ ПОЛЬЗОВАТЕЛЕМ ПОСЛЕ ADMIN RESET")
    client.clear_bearer_token()
    test_login_payload = client.login_via_token_endpoint(
        username=updated_username_by_admin,
        password=reset_password,
    )
    print_json(test_login_payload)

    # Сохраняем токен тестового пользователя.
    test_user_access_token = test_login_payload["access_token"]

    # Устанавливаем токен тестового пользователя.
    client.set_bearer_token(test_user_access_token)

    # 13. Self-update профиля тестового пользователя.
    print_block("13. SELF-UPDATE ПРОФИЛЯ ТЕСТОВОГО ПОЛЬЗОВАТЕЛЯ")
    self_update_payload = {
        "email": test_email,
        "username": updated_username_by_self,
    }
    response = client.patch_json("/users/me/update", self_update_payload)
    assert_status(response, 200, "PATCH /users/me/update")
    self_update_response_payload = response.json()
    print_json(self_update_response_payload)

    # 14. Смена своего пароля тестовым пользователем.
    print_block("14. СМЕНА СВОЕГО ПАРОЛЯ")
    change_password_payload = {
        "current_password": reset_password,
        "new_password": changed_password,
    }
    response = client.post_json("/users/me/change-password", change_password_payload)
    assert_status(response, 200, "POST /users/me/change-password")
    change_password_response_payload = response.json()
    print_json(change_password_response_payload)

    # 15. Повторный логин после self password change.
    print_block("15. ПОВТОРНЫЙ ЛОГИН ПОСЛЕ SELF PASSWORD CHANGE")
    client.clear_bearer_token()
    relogin_payload = client.login_via_token_endpoint(
        username=updated_username_by_self,
        password=changed_password,
    )
    print_json(relogin_payload)

    # Возвращаем admin token для дальнейших административных действий.
    client.set_bearer_token(admin_access_token)

    # 16. Снятие роли.
    print_block("16. СНЯТИЕ РОЛИ")
    revoke_role_payload = {
        "role_code": assign_role_code,
    }
    response = client.post_json(f"/users/{created_user_id}/roles/revoke", revoke_role_payload)
    assert_status(response, 200, f"POST /users/{created_user_id}/roles/revoke")
    revoked_role_payload = response.json()
    print_json(revoked_role_payload)

    # 17. Деактивация пользователя.
    print_block("17. ДЕАКТИВАЦИЯ ПОЛЬЗОВАТЕЛЯ")
    response = client.post_json(f"/users/{created_user_id}/deactivate", {})
    assert_status(response, 200, f"POST /users/{created_user_id}/deactivate")
    deactivated_user_payload = response.json()
    print_json(deactivated_user_payload)

    # Финальный блок.
    print_block("СЦЕНАРИЙ ЗАВЕРШЁН УСПЕШНО")
    print("Все основные тесты auth/users выполнены без ошибок.")


# Точка входа в скрипт.
if __name__ == "__main__":
    # Создаём парсер аргументов командной строки.
    parser = argparse.ArgumentParser(
        description="Интеграционный smoke-test для auth/users API FitIntel Pro"
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

    # Аргумент role_code для теста assign/revoke.
    parser.add_argument(
        "--assign-role-code",
        default="manager",
        help="Код роли для теста назначения/снятия, по умолчанию manager",
    )

    # Читаем аргументы.
    args = parser.parse_args()

    # Запускаем сценарий в общем блоке try/except.
    try:
        run_scenario(
            base_url=args.base_url,
            admin_login=args.admin_login,
            admin_password=args.admin_password,
            assign_role_code=args.assign_role_code,
        )
    except TestScenarioError as exc:
        # Печатаем понятную ошибку тестового сценария.
        print_block("ОШИБКА ТЕСТОВОГО СЦЕНАРИЯ")
        print(str(exc))
        sys.exit(1)
    except requests.RequestException as exc:
        # Печатаем сетевую ошибку, если API недоступен.
        print_block("СЕТЕВАЯ ОШИБКА")
        print(str(exc))
        sys.exit(2)
    except Exception as exc:
        # Печатаем непредвиденную ошибку.
        print_block("НЕОЖИДАННАЯ ОШИБКА")
        print(str(exc))
        sys.exit(3)