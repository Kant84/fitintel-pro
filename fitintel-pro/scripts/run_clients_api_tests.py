# scripts/run_clients_api_tests.py

# импорт os для работы с переменными окружения
import os

# импорт sys для завершения программы
import sys

# импорт time для пауз и ожиданий
import time

# импорт socket для проверки доступности порта
import socket

# импорт subprocess для запуска внешних процессов
import subprocess

# импорт pathlib для путей
from pathlib import Path

# импорт requests для HTTP-запросов
import requests


# ============================================================
# НАСТРОЙКИ
# ============================================================

# корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# health endpoint
HEALTH_URL = "http://127.0.0.1:8000/api/v1/health/"

# базовый URL API
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# путь к файлу тестов
PYTEST_FILE = PROJECT_ROOT / "tests" / "integration" / "test_clients_api.py"

# html-отчёт pytest
PYTEST_HTML_REPORT = PROJECT_ROOT / "tests" / "reports" / "clients_api_report.html"

# путь к pg_ctl
PG_CTL_PATH = r"C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"

# путь к данным PostgreSQL
PG_DATA_DIR = r"C:\pgsql\data"

# путь к логам PostgreSQL
PG_LOG_FILE = r"C:\Temp\pglogs\server5433.log"

# логин администратора
LOGIN_VALUE = "admin@fitnexus.local"

# пароль администратора
PASSWORD_VALUE = "admin123"

# логин endpoint
LOGIN_URL = f"{API_BASE_URL}/auth/login"

# endpoint текущего пользователя
ME_URL = f"{API_BASE_URL}/users/me"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

# функция печатает заголовок блока
def print_block(title: str) -> None:
    # печатаем пустую строку
    print()

    # печатаем линию
    print("=" * 80)

    # печатаем заголовок
    print(title)

    # печатаем линию
    print("=" * 80)


# функция проверяет, доступен ли порт
def is_port_open(host: str, port: int) -> bool:
    # создаём сокет
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # задаём короткий таймаут
        sock.settimeout(1)

        # пытаемся подключиться к порту
        result = sock.connect_ex((host, port))

        # код 0 значит, что порт открыт
        return result == 0


# функция получает PID процессов на порту
def get_pids_on_port(port: int) -> list[int]:
    # запускаем netstat
    process = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        shell=False,
    )

    # если netstat отработал с ошибкой — возвращаем пустой список
    if process.returncode != 0:
        return []

    # список PID
    pids = []

    # перебираем строки вывода
    for line in process.stdout.splitlines():
        # проверяем наличие нужного порта
        if f":{port}" not in line:
            continue

        # нас интересует только LISTENING
        if "LISTENING" not in line:
            continue

        # разбиваем строку на части
        parts = line.split()

        # если формат неожиданный — пропускаем
        if len(parts) < 5:
            continue

        # PID обычно в последнем столбце
        pid_value = parts[-1]

        # если это число — сохраняем
        if pid_value.isdigit():
            pids.append(int(pid_value))

    # возвращаем PID
    return pids


# функция убивает процесс по PID
def kill_process(pid: int) -> None:
    # печатаем сообщение
    print(f"Убиваем процесс PID={pid}")

    # выполняем taskkill
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F"],
        check=False,
        shell=False,
    )


# функция запускает PostgreSQL
def start_postgres() -> None:
    # если pg_ctl не найден — просто сообщаем
    if not Path(PG_CTL_PATH).exists():
        print(f"pg_ctl не найден: {PG_CTL_PATH}")
        return

    # создаём каталог для логов
    Path(PG_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    # печатаем сообщение
    print("Запускаем PostgreSQL...")

    # запускаем pg_ctl
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


# функция запускает uvicorn
def start_uvicorn() -> subprocess.Popen:
    # печатаем сообщение
    print("Запускаем Uvicorn...")

    # запускаем сервер
    process = subprocess.Popen(
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

    # возвращаем процесс
    return process


# функция ожидает готовность API через health endpoint
def wait_for_api(timeout_seconds: int = 30) -> bool:
    # запоминаем время старта ожидания
    started_at = time.time()

    # ждём, пока не выйдем за лимит
    while time.time() - started_at < timeout_seconds:
        try:
            # проверяем health endpoint
            response = requests.get(HEALTH_URL, timeout=3)

            # если health отвечает 200 — API готов
            if response.status_code == 200:
                return True

        except requests.RequestException:
            pass

        # пауза между попытками
        time.sleep(1)

    # если время вышло — API не готов
    return False


# функция получает токен через login endpoint
def login_and_get_token() -> str:
    # печатаем сообщение
    print("Пытаемся получить access token...")

    # варианты payload для login endpoint
    payload_variants = [
        {"username": LOGIN_VALUE, "password": PASSWORD_VALUE},
        {"email": LOGIN_VALUE, "password": PASSWORD_VALUE},
        {"login": LOGIN_VALUE, "password": PASSWORD_VALUE},
    ]

    # сначала пробуем JSON-варианты
    for payload in payload_variants:
        try:
            # отправляем POST-запрос
            response = requests.post(
                LOGIN_URL,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=10,
            )

            # если логин успешный — проверяем токен
            if response.status_code in (200, 201):
                data = response.json()

                # если токен есть — возвращаем
                if "access_token" in data:
                    return data["access_token"]

            # если ошибка 401 — пароль неверный
            if response.status_code == 401:
                raise RuntimeError("Неверный логин или пароль при обращении к /auth/login")

        except requests.RequestException:
            pass

    # затем пробуем form-data вариант
    form_variants = [
        {"username": LOGIN_VALUE, "password": PASSWORD_VALUE},
        {"grant_type": "password", "username": LOGIN_VALUE, "password": PASSWORD_VALUE},
    ]

    # перебираем варианты form-data
    for form_data in form_variants:
        try:
            # отправляем POST-запрос
            response = requests.post(
                LOGIN_URL,
                data=form_data,
                headers={"Accept": "application/json"},
                timeout=10,
            )

            # если логин успешный — возвращаем токен
            if response.status_code in (200, 201):
                data = response.json()

                # если access_token найден — возвращаем его
                if "access_token" in data:
                    return data["access_token"]

            # если 401 — пароль неверный
            if response.status_code == 401:
                raise RuntimeError("Неверный логин или пароль при form-login")

        except requests.RequestException:
            pass

    # если ничего не подошло — возвращаем понятную ошибку
    raise RuntimeError(
        "Не удалось получить access token. Проверь LOGIN_VALUE, PASSWORD_VALUE и формат /auth/login"
    )


# функция получает id текущего пользователя
def get_current_user_id(token: str) -> str:
    # формируем заголовки авторизации
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    # делаем GET-запрос
    response = requests.get(
        ME_URL,
        headers=headers,
        timeout=10,
    )

    # если ответ не 200 — сообщаем об ошибке
    if response.status_code != 200:
        raise RuntimeError(
            f"Не удалось получить /users/me. Код={response.status_code}. Тело={response.text}"
        )

    # разбираем JSON
    data = response.json()

    # проверяем наличие id
    if "id" not in data:
        raise RuntimeError("В ответе /users/me нет поля id")

    # возвращаем id
    return data["id"]


# функция запускает pytest с HTML-отчётом
def run_pytest(token: str, user_id: str) -> int:
    # создаём каталог отчётов
    PYTEST_HTML_REPORT.parent.mkdir(parents=True, exist_ok=True)

    # копируем окружение
    env = os.environ.copy()

    # подставляем переменные окружения
    env["TEST_API_BASE_URL"] = API_BASE_URL
    env["TEST_API_TOKEN"] = token
    env["TEST_USER_ID"] = user_id

    # печатаем сообщение
    print("Запускаем pytest с HTML-отчётом...")

    # запускаем pytest
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(PYTEST_FILE),
            "-v",
            f"--html={PYTEST_HTML_REPORT}",
            "--self-contained-html",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        shell=False,
    )

    # печатаем путь к отчёту
    print(f"HTML-отчёт: {PYTEST_HTML_REPORT}")

    # возвращаем код завершения
    return result.returncode


# ============================================================
# ОСНОВНОЙ СЦЕНАРИЙ
# ============================================================

def main() -> int:
    # проверка логина и пароля
    print_block("Шаг 1. Проверка логина и пароля")

    # если пароль не заменён — сразу останавливаемся
    if PASSWORD_VALUE == "CHANGE_ME_REAL_PASSWORD":
        print("Ошибка: в файле scripts/run_clients_api_tests.py не задан реальный PASSWORD_VALUE")
        return 1

    # освобождаем порт 8000
    print_block("Шаг 2. Освобождаем порт 8000")

    # находим процессы на порту
    pids = get_pids_on_port(8000)

    # убиваем найденные процессы
    for pid in pids:
        kill_process(pid)

    # ждём чуть-чуть после убийства процессов
    time.sleep(2)

    # запускаем PostgreSQL
    print_block("Шаг 3. Запускаем PostgreSQL")
    start_postgres()
    time.sleep(3)

    # запускаем Uvicorn
    print_block("Шаг 4. Запускаем Uvicorn")
    uvicorn_process = start_uvicorn()

    try:
        # ждём готовность API
        print_block("Шаг 5. Ждём /api/v1/health/")

        # ожидаем API
        if not wait_for_api(timeout_seconds=30):
            print("Ошибка: health endpoint не поднялся вовремя")
            return 1

        # сообщаем, что API доступен
        print("Health endpoint доступен")

        # получаем access token
        print_block("Шаг 6. Получаем access token")
        token = login_and_get_token()
        print(f"Токен получен: {token[:20]}...")

        # получаем current user id
        print_block("Шаг 7. Получаем current user id")
        user_id = get_current_user_id(token)
        print(f"Current user id: {user_id}")

        # запускаем pytest
        print_block("Шаг 8. Запускаем pytest")
        pytest_exit_code = run_pytest(token, user_id)

        # возвращаем код pytest
        return pytest_exit_code

    finally:
        # останавливаем Uvicorn
        print_block("Шаг 9. Останавливаем Uvicorn")

        # если процесс ещё жив — завершаем
        if uvicorn_process.poll() is None:
            uvicorn_process.terminate()
            time.sleep(2)

            # если мягкое завершение не помогло — убиваем
            if uvicorn_process.poll() is None:
                uvicorn_process.kill()


# стандартная точка входа
if __name__ == "__main__":
    raise SystemExit(main())