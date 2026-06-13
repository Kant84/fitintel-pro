# scripts/test_core_platform_full_api.py

# Импорт argparse для чтения параметров командной строки.
import argparse

# Импорт json для красивого вывода JSON.
import json

# Импорт sys для корректного завершения программы с кодом возврата.
import sys

# Импорт uuid4 для генерации уникальных логинов и email.
from uuid import uuid4

# Импорт requests для HTTP-запросов к API.
import requests


# Базовый класс ошибки тестового сценария.
class TestScenarioError(Exception):
    # Класс-пустышка нужен для понятного разделения типов ошибок.
    pass


# Функция печатает красивый заголовок блока.
def print_block(title: str) -> None:
    # Печатаем пустую строку и линию разделителя.
    print("\n" + "=" * 80)
    # Печатаем заголовок текущего шага.
    print(title)
    # Печатаем нижнюю линию разделителя.
    print("=" * 80)


# Функция печатает JSON красиво.
def print_json(data) -> None:
    # Преобразуем объект в форматированный JSON.
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


# Функция печатает короткий статус.
def print_status(label: str, status_value: str) -> None:
    # Печатаем краткую строку статуса.
    print(f"[{status_value}] {label}")


# Функция проверяет HTTP-статус ответа.
def assert_status(response: requests.Response, expected_status: int, step_name: str) -> None:
    # Если статус ответа не совпадает с ожидаемым, поднимаем понятную ошибку.
    if response.status_code != expected_status:
        # Пытаемся разобрать ответ как JSON.
        try:
            error_payload = response.json()
        except Exception:
            # Если JSON не разобрался, берём текст ответа.
            error_payload = response.text

        # Выбрасываем исключение с подробным описанием проблемы.
        raise TestScenarioError(
            f"[{step_name}] Ожидался статус {expected_status}, "
            f"но получен {response.status_code}. Ответ:\n{error_payload}"
        )


# Класс HTTP-клиента для API.
class ApiClient:
    # Конструктор клиента.
    def __init__(self, base_url: str):
        # Сохраняем базовый URL без завершающего слеша.
        self.base_url = base_url.rstrip("/")

        # Создаём HTTP-сессию.
        self.session = requests.Session()

    # Метод устанавливает bearer token в заголовки.
    def set_bearer_token(self, access_token: str) -> None:
        # Устанавливаем заголовок Authorization.
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    # Метод удаляет bearer token.
    def clear_bearer_token(self) -> None:
        # Удаляем заголовок Authorization, если он был.
        self.session.headers.pop("Authorization", None)

    # Метод выполняет GET-запрос.
    def get(self, path: str, params: dict | None = None) -> requests.Response:
        # Выполняем GET-запрос к указанному пути.
        return self.session.get(f"{self.base_url}{path}", params=params, timeout=30)

    # Метод выполняет POST-запрос с JSON.
    def post_json(self, path: str, payload: dict) -> requests.Response:
        # Выполняем POST-запрос с JSON-телом.
        return self.session.post(f"{self.base_url}{path}", json=payload, timeout=30)

    # Метод выполняет PATCH-запрос с JSON.
    def patch_json(self, path: str, payload: dict) -> requests.Response:
        # Выполняем PATCH-запрос с JSON-телом.
        return self.session.patch(f"{self.base_url}{path}", json=payload, timeout=30)

    # Метод выполняет логин через /auth/token.
    def login_via_token_endpoint(self, username: str, password: str) -> dict:
        # Формируем полный URL для логина.
        url = f"{self.base_url}/auth/token"

        # Формируем form-data согласно OAuth2PasswordRequestForm.
        form_data = {
            "username": username,
            "password": password,
        }

        # Отправляем POST-запрос на логин.
        response = self.session.post(url, data=form_data, timeout=30)

        # Проверяем успешность логина.
        assert_status(response, 200, "Логин через /auth/token")

        # Возвращаем JSON-ответ.
        return response.json()


# Функция пробует вызвать endpoint и, если его нет, помечает шаг как пропущенный.
def try_optional_get(client: ApiClient, path: str, params: dict | None, step_name: str):
    # Выполняем GET-запрос.
    response = client.get(path, params=params)

    # Если endpoint отсутствует, возвращаем специальный результат.
    if response.status_code == 404:
        print_status(step_name, "SKIPPED")
        return None

    # Если статус не 200, это уже ошибка.
    assert_status(response, 200, step_name)

    # Возвращаем JSON ответа.
    return response.json()


# Главная функция полного сценария.
def run_full_scenario(
    base_url: str,
    admin_login: str,
    admin_password: str,
    assign_role_code: str,
    check_permission_code: str,
) -> None:
    # Создаём API-клиент.
    client = ApiClient(base_url=base_url)

    # Генерируем уникальный суффикс для тестового пользователя.
    unique_suffix = uuid4().hex[:8]

    # Формируем тестовые данные пользователя.
    test_username = f"test_user_{unique_suffix}"
    test_email = f"test_{unique_suffix}@example.local"
    test_password = "TempPass123!"
    reset_password = "ResetPass123!"
    changed_password = "ChangedPass123!"
    updated_username_by_admin = f"{test_username}_admin"
    updated_username_by_self = f"{test_username}_self"

    # Переменные для идентификаторов и токенов.
    created_user_id = None
    admin_access_token = None
    test_user_access_token = None

    # ============================================================
    # AUTH
    # ============================================================

    # 1. Логин администратором.
    print_block("1. ЛОГИН АДМИНИСТРАТОРОМ")
    admin_login_payload = client.login_via_token_endpoint(
        username=admin_login,
        password=admin_password,
    )
    print_json(admin_login_payload)

    # Сохраняем access token администратора.
    admin_access_token = admin_login_payload["access_token"]

    # Устанавливаем token в заголовки.
    client.set_bearer_token(admin_access_token)

    # 2. Проверка /auth/me.
    print_block("2. ПРОВЕРКА /auth/me")
    response = client.get("/auth/me")
    assert_status(response, 200, "GET /auth/me")
    print_json(response.json())

    # 3. Проверка /users/me.
    print_block("3. ПРОВЕРКА /users/me")
    response = client.get("/users/me")
    assert_status(response, 200, "GET /users/me")
    print_json(response.json())

    # ============================================================
    # USERS
    # ============================================================

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
    response = client.get("/users/", params={"offset": 0, "limit": 50})
    assert_status(response, 200, "GET /users/")
    print_json(response.json())

    # 6. Чтение пользователя по UUID.
    print_block("6. ЧТЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО UUID")
    response = client.get(f"/users/{created_user_id}")
    assert_status(response, 200, f"GET /users/{created_user_id}")
    print_json(response.json())

    # 7. Административное обновление пользователя.
    print_block("7. ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ АДМИНИСТРАТОРОМ")
    update_payload = {
        "email": test_email,
        "username": updated_username_by_admin,
        "is_active": True,
    }
    response = client.patch_json(f"/users/{created_user_id}", update_payload)
    assert_status(response, 200, f"PATCH /users/{created_user_id}")
    print_json(response.json())

    # ============================================================
    # ROLE ASSIGN / READ
    # ============================================================

    # 8. Назначение роли пользователю.
    print_block("8. НАЗНАЧЕНИЕ РОЛИ ПОЛЬЗОВАТЕЛЮ")
    assign_role_payload = {
        "role_code": assign_role_code,
    }
    response = client.post_json(f"/users/{created_user_id}/roles/assign", assign_role_payload)
    assert_status(response, 200, f"POST /users/{created_user_id}/roles/assign")
    print_json(response.json())

    # 9. Чтение ролей пользователя.
    print_block("9. ЧТЕНИЕ РОЛЕЙ ПОЛЬЗОВАТЕЛЯ")
    response = client.get(f"/users/{created_user_id}/roles")
    assert_status(response, 200, f"GET /users/{created_user_id}/roles")
    print_json(response.json())

    # 10. Чтение permissions пользователя.
    print_block("10. ЧТЕНИЕ PERMISSIONS ПОЛЬЗОВАТЕЛЯ")
    response = client.get(f"/users/{created_user_id}/permissions")
    assert_status(response, 200, f"GET /users/{created_user_id}/permissions")
    print_json(response.json())

    # ============================================================
    # PASSWORD FLOWS
    # ============================================================

    # 11. Административный сброс пароля.
    print_block("11. АДМИНИСТРАТИВНЫЙ СБРОС ПАРОЛЯ")
    reset_password_payload = {
        "new_password": reset_password,
        "force_password_change": True,
    }
    response = client.post_json(f"/users/{created_user_id}/reset-password", reset_password_payload)
    assert_status(response, 200, f"POST /users/{created_user_id}/reset-password")
    print_json(response.json())

    # 12. Логин тестовым пользователем после admin reset.
    print_block("12. ЛОГИН ТЕСТОВЫМ ПОЛЬЗОВАТЕЛЕМ ПОСЛЕ ADMIN RESET")
    client.clear_bearer_token()
    test_login_payload = client.login_via_token_endpoint(
        username=updated_username_by_admin,
        password=reset_password,
    )
    print_json(test_login_payload)

    # Сохраняем токен тестового пользователя.
    test_user_access_token = test_login_payload["access_token"]

    # Устанавливаем token тестового пользователя.
    client.set_bearer_token(test_user_access_token)

    # 13. Self-update профиля.
    print_block("13. SELF-UPDATE ПРОФИЛЯ ТЕСТОВОГО ПОЛЬЗОВАТЕЛЯ")
    self_update_payload = {
        "email": test_email,
        "username": updated_username_by_self,
    }
    response = client.patch_json("/users/me/update", self_update_payload)
    assert_status(response, 200, "PATCH /users/me/update")
    print_json(response.json())

    # 14. Смена своего пароля.
    print_block("14. СМЕНА СВОЕГО ПАРОЛЯ")
    change_password_payload = {
        "current_password": reset_password,
        "new_password": changed_password,
    }
    response = client.post_json("/users/me/change-password", change_password_payload)
    assert_status(response, 200, "POST /users/me/change-password")
    print_json(response.json())

    # 15. Повторный логин после self password change.
    print_block("15. ПОВТОРНЫЙ ЛОГИН ПОСЛЕ SELF PASSWORD CHANGE")
    client.clear_bearer_token()
    relogin_payload = client.login_via_token_endpoint(
        username=updated_username_by_self,
        password=changed_password,
    )
    print_json(relogin_payload)

    # ============================================================
    # RBAC OPTIONAL
    # ============================================================

    # Используем токен администратора для диагностических RBAC-ручек.
    client.set_bearer_token(admin_access_token)

    # 16. RBAC check-access, если endpoint существует.
    print_block("16. RBAC CHECK-ACCESS (если ручка существует)")
    rb_check = try_optional_get(
        client=client,
        path="/rbac/check-access",
        params={
            "user_id": created_user_id,
            "permission_code": check_permission_code,
        },
        step_name="GET /rbac/check-access",
    )
    if rb_check is not None:
        print_json(rb_check)

    # 17. RBAC explain-access, если endpoint существует.
    print_block("17. RBAC EXPLAIN-ACCESS (если ручка существует)")
    rb_explain = try_optional_get(
        client=client,
        path="/rbac/explain-access",
        params={
            "user_id": created_user_id,
            "permission_code": check_permission_code,
        },
        step_name="GET /rbac/explain-access",
    )
    if rb_explain is not None:
        print_json(rb_explain)

    # 18. RBAC snapshot, если endpoint существует.
    print_block("18. RBAC SNAPSHOT (если ручка существует)")
    rb_snapshot = try_optional_get(
        client=client,
        path=f"/rbac/snapshot/{created_user_id}",
        params=None,
        step_name="GET /rbac/snapshot/{user_id}",
    )
    if rb_snapshot is not None:
        print_json(rb_snapshot)

    # 19. RBAC missing-permissions, если endpoint существует.
    print_block("19. RBAC MISSING-PERMISSIONS (если ручка существует)")
    response = client.get(
        "/rbac/missing-permissions",
        params=[
            ("user_id", created_user_id),
            ("required_permissions", check_permission_code),
            ("required_permissions", "users.read"),
        ],
    )
    if response.status_code == 404:
        print_status("GET /rbac/missing-permissions", "SKIPPED")
    else:
        assert_status(response, 200, "GET /rbac/missing-permissions")
        print_json(response.json())

    # 20. RBAC debug-access, если endpoint существует.
    print_block("20. RBAC DEBUG-ACCESS (если ручка существует)")
    response = client.get(
        "/rbac/debug-access",
        params=[
            ("user_id", created_user_id),
            ("required_permissions", check_permission_code),
            ("required_permissions", "users.read"),
        ],
    )
    if response.status_code == 404:
        print_status("GET /rbac/debug-access", "SKIPPED")
    else:
        assert_status(response, 200, "GET /rbac/debug-access")
        print_json(response.json())

    # 21. RBAC health, если endpoint существует.
    print_block("21. RBAC HEALTH (если ручка существует)")
    rb_health = try_optional_get(
        client=client,
        path="/rbac/health",
        params=None,
        step_name="GET /rbac/health",
    )
    if rb_health is not None:
        print_json(rb_health)

    # ============================================================
    # CLEANUP
    # ============================================================

    # Возвращаем admin token для cleanup.
    client.set_bearer_token(admin_access_token)

    # 22. Снятие роли.
    print_block("22. СНЯТИЕ РОЛИ")
    revoke_role_payload = {
        "role_code": assign_role_code,
    }
    response = client.post_json(f"/users/{created_user_id}/roles/revoke", revoke_role_payload)
    assert_status(response, 200, f"POST /users/{created_user_id}/roles/revoke")
    print_json(response.json())

    # 23. Деактивация пользователя.
    print_block("23. ДЕАКТИВАЦИЯ ПОЛЬЗОВАТЕЛЯ")
    response = client.post_json(f"/users/{created_user_id}/deactivate", {})
    assert_status(response, 200, f"POST /users/{created_user_id}/deactivate")
    print_json(response.json())

    # 24. Попытка логина деактивированным пользователем.
    print_block("24. ПРОВЕРКА, ЧТО ДЕАКТИВИРОВАННЫЙ ПОЛЬЗОВАТЕЛЬ НЕ ЛОГИНИТСЯ")
    client.clear_bearer_token()
    response = client.session.post(
        f"{client.base_url}/auth/token",
        data={
            "username": updated_username_by_self,
            "password": changed_password,
        },
        timeout=30,
    )

    # Ожидаем 401 или 403 в зависимости от текущей реализации auth.
    if response.status_code not in (401, 403):
        raise TestScenarioError(
            f"[POST /auth/token после deactivate] Ожидался статус 401 или 403, "
            f"но получен {response.status_code}. Ответ:\n{response.text}"
        )

    # Печатаем ответ.
    try:
        print_json(response.json())
    except Exception:
        print(response.text)

    # Финальный блок.
    print_block("СЦЕНАРИЙ ЗАВЕРШЁН УСПЕШНО")
    print("Полный smoke-test блока Core Platform / auth / users / RBAC завершён без ошибок.")


# Точка входа.
if __name__ == "__main__":
    # Создаём парсер аргументов.
    parser = argparse.ArgumentParser(
        description="Полный smoke/integration test для Core Platform / auth / users / RBAC"
    )

    # Аргумент базового URL.
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

    # Аргумент role_code для назначения роли.
    parser.add_argument(
        "--assign-role-code",
        default="manager",
        help="Код роли для теста назначения/снятия, по умолчанию manager",
    )

    # Аргумент permission_code для RBAC check/explain.
    parser.add_argument(
        "--check-permission-code",
        default="users.read",
        help="Permission code для проверки RBAC, по умолчанию users.read",
    )

    # Читаем аргументы.
    args = parser.parse_args()

    # Запускаем общий сценарий с обработкой ошибок.
    try:
        run_full_scenario(
            base_url=args.base_url,
            admin_login=args.admin_login,
            admin_password=args.admin_password,
            assign_role_code=args.assign_role_code,
            check_permission_code=args.check_permission_code,
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
        
#  python scripts/test_core_platform_full_api.py --base-url http://127.0.0.1:8000/api/v1 --admin-login admin --admin-password admin123 --assign-role-code manager --check-permission-code users.read      