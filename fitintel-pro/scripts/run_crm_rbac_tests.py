# scripts/run_crm_rbac_tests.py

# импорт os
import os

# импорт sys
import sys

# импорт time
import time

# импорт socket
import socket

# импорт subprocess
import subprocess

# импорт pathlib
from pathlib import Path

# импорт uuid
import uuid

# импорт requests
import requests


# ============================================================
# НАСТРОЙКИ
# ============================================================

# корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# адрес health endpoint
HEALTH_URL = "http://127.0.0.1:8000/api/v1/health/"

# базовый адрес API
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# путь к html-отчёту
PYTEST_HTML_REPORT = PROJECT_ROOT / "tests" / "reports" / "crm_rbac_report.html"

# путь к pg_ctl
PG_CTL_PATH = r"C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"

# путь к данным PostgreSQL
PG_DATA_DIR = r"C:\pgsql\data"

# путь к логам PostgreSQL
PG_LOG_FILE = r"C:\Temp\pglogs\server5433.log"

# логин администратора
ADMIN_LOGIN = "admin@fitnexus.local"

# пароль администратора
ADMIN_PASSWORD = "admin123"


# ============================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================

# печать блока
def print_block(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


# проверка, открыт ли порт
def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result == 0


# получить pid процессов на порту
def get_pids_on_port(port: int) -> list[int]:
    process = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        shell=False,
    )

    if process.returncode != 0:
        return []

    pids = []

    for line in process.stdout.splitlines():
        if f":{port}" not in line:
            continue
        if "LISTENING" not in line:
            continue

        parts = line.split()
        if len(parts) < 5:
            continue

        pid_value = parts[-1]
        if pid_value.isdigit():
            pids.append(int(pid_value))

    return pids


# убить процесс
def kill_process(pid: int) -> None:
    print(f"Убиваем процесс PID={pid}")
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F"],
        check=False,
        shell=False,
    )


# запуск PostgreSQL
def start_postgres() -> None:
    if not Path(PG_CTL_PATH).exists():
        print(f"pg_ctl не найден: {PG_CTL_PATH}")
        return

    Path(PG_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    print("Запускаем PostgreSQL...")

    subprocess.run(
        [
            PG_CTL_PATH,
            "-D",
            PG_DATA_DIR,
            "-l",
            PG_LOG_FILE,
            "start",
        ],
        check=False,
        shell=False,
    )


# запуск uvicorn
def start_uvicorn() -> subprocess.Popen:
    print("Запускаем Uvicorn...")

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            "8000",
        ],
        cwd=str(PROJECT_ROOT),
    )


# ожидание health
def wait_for_health(timeout_seconds: int = 30) -> bool:
    started_at = time.time()

    while time.time() - started_at < timeout_seconds:
        try:
            response = requests.get(HEALTH_URL, timeout=3)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass

        time.sleep(1)

    return False


# логин и получение токена
def login_and_get_token(login_value: str, password_value: str) -> str:
    login_url = f"{API_BASE_URL}/auth/login"

    payload_variants = [
        {"username": login_value, "password": password_value},
        {"email": login_value, "password": password_value},
        {"login": login_value, "password": password_value},
    ]

    for payload in payload_variants:
        try:
            response = requests.post(
                login_url,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=10,
            )

            if response.status_code in (200, 201):
                data = response.json()
                if "access_token" in data:
                    return data["access_token"]

        except requests.RequestException:
            pass

    form_variants = [
        {"username": login_value, "password": password_value},
        {"grant_type": "password", "username": login_value, "password": password_value},
    ]

    for form_data in form_variants:
        try:
            response = requests.post(
                login_url,
                data=form_data,
                headers={"Accept": "application/json"},
                timeout=10,
            )

            if response.status_code in (200, 201):
                data = response.json()
                if "access_token" in data:
                    return data["access_token"]

        except requests.RequestException:
            pass

    raise RuntimeError(f"Не удалось получить токен для {login_value}")


# заголовки
def build_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# получить список пользователей
def list_users(admin_token: str) -> list[dict]:
    response = requests.get(
        f"{API_BASE_URL}/users/",
        headers=build_headers(admin_token),
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("items", [])


# получить список ролей
def list_roles(admin_token: str) -> list[dict]:
    response = requests.get(
        f"{API_BASE_URL}/roles/",
        headers=build_headers(admin_token),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


# найти пользователя по email
def find_user_by_email(admin_token: str, email: str) -> dict | None:
    users = list_users(admin_token)

    for user in users:
        if user.get("email") == email:
            return user

    return None


# найти роль по code
def find_role_by_code(admin_token: str, role_code: str) -> dict | None:
    roles = list_roles(admin_token)

    for role in roles:
        if role.get("code") == role_code:
            return role

    return None


# создать пользователя
def create_user(admin_token: str, email: str, password: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/users/",
        headers=build_headers(admin_token),
        json={
            "email": email,
            "username": email,
            "phone": None,
            "password": password,
            "is_active": True,
            "is_superuser": False,
            "is_verified": True,
        },
        timeout=15,
    )

    response.raise_for_status()
    return response.json()


# назначить роль пользователю
def assign_role(admin_token: str, user_id: str, role_id: str) -> None:
    response = requests.post(
        f"{API_BASE_URL}/rbac/users/{user_id}/roles/{role_id}",
        headers=build_headers(admin_token),
        timeout=15,
    )

    # 200/201/409 считаем допустимыми
    if response.status_code not in (200, 201, 409):
        raise RuntimeError(
            f"Не удалось назначить роль. Код={response.status_code}. Тело={response.text}"
        )


# создать или получить тестового пользователя
def ensure_role_user(admin_token: str, role_code: str, password: str) -> tuple[str, str]:
    email = f"test_{role_code}@fitnexus.local"

    # ищем пользователя
    user = find_user_by_email(admin_token, email)

    # если нет — создаём
    if user is None:
        user = create_user(admin_token, email, password)

    # ищем роль
    role = find_role_by_code(admin_token, role_code)
    if role is None:
        raise RuntimeError(f"Роль {role_code} не найдена")

    # назначаем роль
    assign_role(admin_token, user["id"], role["id"])

    # возвращаем логин и пароль
    return email, password


# ============================================================
# ОСНОВНОЙ СЦЕНАРИЙ
# ============================================================

def main() -> int:
    print_block("Шаг 1. Проверка admin логина и пароля")

    if ADMIN_PASSWORD == "CHANGE_ME_REAL_PASSWORD":
        print("Ошибка: в scripts/run_crm_rbac_tests.py не задан реальный ADMIN_PASSWORD")
        return 1

    print_block("Шаг 2. Освобождаем порт 8000")
    pids = get_pids_on_port(8000)
    for pid in pids:
        kill_process(pid)

    time.sleep(2)

    print_block("Шаг 3. Запускаем PostgreSQL")
    start_postgres()
    time.sleep(3)

    print_block("Шаг 4. Запускаем Uvicorn")
    uvicorn_process = start_uvicorn()

    try:
        print_block("Шаг 5. Ждём /api/v1/health/")
        if not wait_for_health(timeout_seconds=30):
            print("Ошибка: health endpoint не поднялся")
            return 1

        print("Health endpoint доступен")

        print_block("Шаг 6. Логинимся под admin")
        admin_token = login_and_get_token(ADMIN_LOGIN, ADMIN_PASSWORD)
        print(f"Admin token получен: {admin_token[:20]}...")

        print_block("Шаг 7. Готовим тестовых пользователей ролей")

        # один и тот же пароль для тестовых пользователей
        role_user_password = "TestRole123!"

        manager_login, manager_password = ensure_role_user(admin_token, "manager", role_user_password)
        trainer_login, trainer_password = ensure_role_user(admin_token, "trainer", role_user_password)
        cashier_login, cashier_password = ensure_role_user(admin_token, "cashier", role_user_password)
        support_login, support_password = ensure_role_user(admin_token, "support", role_user_password)

        print("Пользователи ролей готовы")

        print_block("Шаг 8. Получаем токены ролей")
        manager_token = login_and_get_token(manager_login, manager_password)
        trainer_token = login_and_get_token(trainer_login, trainer_password)
        cashier_token = login_and_get_token(cashier_login, cashier_password)
        support_token = login_and_get_token(support_login, support_password)

        print("Токены ролей получены")

        print_block("Шаг 9. Запускаем RBAC pytest")
        PYTEST_HTML_REPORT.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["TEST_API_BASE_URL"] = API_BASE_URL
        env["TEST_MANAGER_TOKEN"] = manager_token
        env["TEST_TRAINER_TOKEN"] = trainer_token
        env["TEST_CASHIER_TOKEN"] = cashier_token
        env["TEST_SUPPORT_TOKEN"] = support_token

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_clients_rbac.py",
                "tests/integration/test_tariffs_rbac.py",
                "tests/integration/test_subscriptions_rbac.py",
                "-v",
                f"--html={PYTEST_HTML_REPORT}",
                "--self-contained-html",
            ],
            cwd=str(PROJECT_ROOT),
            env=env,
            shell=False,
        )

        print(f"HTML-отчёт: {PYTEST_HTML_REPORT}")
        return result.returncode

    finally:
        print_block("Шаг 10. Останавливаем Uvicorn")
        if uvicorn_process.poll() is None:
            uvicorn_process.terminate()
            time.sleep(2)

            if uvicorn_process.poll() is None:
                uvicorn_process.kill()


if __name__ == "__main__":
    raise SystemExit(main())