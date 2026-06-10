# scripts/run_tariffs_api_tests.py

# импорт os для работы с переменными окружения
import os

# импорт sys для завершения программы
import sys

# импорт time для пауз и ожиданий
import time

# импорт socket для проверки порта
import socket

# импорт subprocess для запуска процессов
import subprocess

# импорт pathlib для работы с путями
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

# путь к тестовому файлу
PYTEST_FILE = PROJECT_ROOT / "tests" / "integration" / "test_tariffs_api.py"

# путь к HTML-отчёту
PYTEST_HTML_REPORT = PROJECT_ROOT / "tests" / "reports" / "tariffs_api_report.html"

# путь к pg_ctl
PG_CTL_PATH = r"C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"

# путь к данным PostgreSQL
PG_DATA_DIR = r"C:\pgsql\data"

# путь к лог-файлу PostgreSQL
PG_LOG_FILE = r"C:\Temp\pglogs\server5433.log"

# логин администратора
LOGIN_VALUE = "admin@fitnexus.local"

# пароль администратора
PASSWORD_VALUE = "admin123"

# URL логина
LOGIN_URL = f"{API_BASE_URL}/auth/login"

# URL текущего пользователя
ME_URL = f"{API_BASE_URL}/users/me"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

# функция печатает заголовок блока
def print_block(title: str) -> None:
    # печатаем пустую строку
    print()

    # печатаем верхнюю линию
    print("=" * 80)

    # печатаем заголовок
    print(title)

    # печатаем нижнюю линию
    print("=" * 80)


# функция проверяет, открыт ли порт
def is_port_open(host: str, port: int) -> bool:
    # создаём сокет
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # задаём короткий таймаут
        sock.settimeout(1)

        # проверяем соединение
        result = sock.connect_ex((host, port))

        # 0 значит порт открыт
        return result == 0


# функция получает PID процессов на заданном порту
def get_pids_on_port(port: int) -> list[int]:
    # запускаем netstat
    process = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        shell=False,
    )

    # если команда упала — возвращаем пустой список
    if process.returncode != 0:
        return []

    # список PID
    pids = []

    # разбираем вывод построчно
    for line in process.stdout.splitlines():
        # пропускаем строки без нужного порта
        if f":{port}" not in line:
            continue

        # оставляем только строки LISTENING
        if "LISTENING" not in line:
            continue

        # делим строку на части
        parts = line.split()

        # если формат неожиданно короткий — пропускаем
        if len(parts) < 5:
            continue

        # PID в последнем столбце
        pid_value = parts[-1]

        # если это число — добавляем
        if pid_value.isdigit():
            pids.append(int(pid_value))

    # возвращаем список PID
    return pids


# функция убивает процесс по PID
def kill_process(pid: int) -> None:
    # печатаем сообщение
    print(f"Убиваем процесс PID={pid}")

    # запускаем taskkill
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

    # создаём папку для логов
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


# функция запускает Uvicorn
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

    # возвращаем объект процесса
    return process


# функция ждёт готовность API через health endpoint
def wait_for_api(timeout_seconds: int = 30) -> bool:
    # запоминаем время старта
    started_at = time.time()

    # крутимся, пока не выйдем за таймаут
    while time.time() - started_at < timeout_seconds:
        try:
            # проверяем health endpoint
            response = requests.get(HEALTH_URL, timeout=3)

            # если health уже доступен — API готов
            if response.status_code == 200:
                return True

        except requests.RequestException:
            pass

        # ждём секунду перед новой попыткой
        time.sleep(1)

    # если время вышло — API не поднялся
    return False


# функция получает access token
def login_and_get_token() -> str:
    # печатаем сообщение
    print("Пытаемся получить access token...")

    # варианты JSON payload
    payload_variants = [
        {"username": LOGIN_VALUE, "password": PASSWORD_VALUE},
        {"email": LOGIN_VALUE, "password": PASSWORD_VALUE},
        {"login": LOGIN_VALUE, "password": PASSWORD_VALUE},
    ]

    # сначала пробуем JSON
    for payload in payload_variants:
        try:
            # отправляем POST-запрос
            response = requests.post(
                LOGIN_URL,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=10,
            )

            # если успешный ответ — ищем токен
            if response.status_code in (200, 201):
                data = response.json()

                # если access_token найден — возвращаем
                if "access_token" in data:
                    return data["access_token"]

            # если 401 — сразу говорим об ошибке логина
            if response.status_code == 401:
                raise RuntimeError("Неверный логин или пароль при JSON-login")

        except requests.RequestException:
            pass

    # затем пробуем form-data
    form_variants = [
        {"username": LOGIN_VALUE, "password": PASSWORD_VALUE},
        {"grant_type": "password", "username": LOGIN_VALUE, "password": PASSWORD_VALUE},
    ]

    # перебираем form-варианты
    for form_data in form_variants:
        try:
            # отправляем POST-запрос
            response = requests.post(
                LOGIN_URL,
                data=form_data,
                headers={"Accept": "application/json"},
                timeout=10,
            )

            # если успешный ответ — ищем токен
            if response.status_code in (200, 201):
                data = response.json()

                # если access_token найден — возвращаем
                if "access_token" in data:
                    return data["access_token"]

            # если 401 — это ошибка логина
            if response.status_code == 401:
                raise RuntimeError("Неверный логин или пароль при form-login")

        except requests.RequestException:
            pass

    # если ни один вариант не подошёл — возвращаем понятную ошибку
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

    # отправляем запрос
    response = requests.get(
        ME_URL,
        headers=headers,
        timeout=10,
    )

    # если ответ не 200 — ошибка
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


# функция запускает pytest и делает HTML-отчёт
def run_pytest(token: str, user_id: str) -> int:
    # создаём папку для отчёта
    PYTEST_HTML_REPORT.parent.mkdir(parents=True, exist_ok=True)

    # копируем окружение
    env = os.environ.copy()

    # подставляем нужные переменные окружения
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

    # печатаем путь к HTML-отчёту
    print(f"HTML-отчёт: {PYTEST_HTML_REPORT}")

    # возвращаем код завершения pytest
    return result.returncode


# ============================================================
# ОСНОВНОЙ СЦЕНАРИЙ
# ============================================================

def main() -> int:
    # шаг 1: проверяем пароль
    print_block("Шаг 1. Проверка логина и пароля")

    # если пароль-заглушка не заменён — останавливаемся
    if PASSWORD_VALUE == "CHANGE_ME_REAL_PASSWORD":
        print("Ошибка: в файле scripts/run_tariffs_api_tests.py не задан реальный PASSWORD_VALUE")
        return 1

    # шаг 2: освобождаем порт
    print_block("Шаг 2. Освобождаем порт 8000")

    # находим процессы на порту
    pids = get_pids_on_port(8000)

    # убиваем найденные процессы
    for pid in pids:
        kill_process(pid)

    # даём системе время освободить порт
    time.sleep(2)

    # шаг 3: запускаем PostgreSQL
    print_block("Шаг 3. Запускаем PostgreSQL")
    start_postgres()
    time.sleep(3)

    # шаг 4: запускаем Uvicorn
    print_block("Шаг 4. Запускаем Uvicorn")
    uvicorn_process = start_uvicorn()

    try:
        # шаг 5: ждём готовность API
        print_block("Шаг 5. Ждём /api/v1/health/")

        # ждём API
        if not wait_for_api(timeout_seconds=30):
            print("Ошибка: health endpoint не поднялся вовремя")
            return 1

        # сообщаем, что API доступен
        print("Health endpoint доступен")

        # шаг 6: получаем токен
        print_block("Шаг 6. Получаем access token")
        token = login_and_get_token()
        print(f"Токен получен: {token[:20]}...")

        # шаг 7: получаем current user id
        print_block("Шаг 7. Получаем current user id")
        user_id = get_current_user_id(token)
        print(f"Current user id: {user_id}")

        # шаг 8: запускаем pytest
        print_block("Шаг 8. Запускаем pytest")
        pytest_exit_code = run_pytest(token, user_id)

        # возвращаем код завершения pytest
        return pytest_exit_code

    finally:
        # шаг 9: останавливаем Uvicorn
        print_block("Шаг 9. Останавливаем Uvicorn")

        # если процесс ещё жив — мягко завершаем
        if uvicorn_process.poll() is None:
            uvicorn_process.terminate()
            time.sleep(2)

            # если не завершился — убиваем принудительно
            if uvicorn_process.poll() is None:
                uvicorn_process.kill()


# стандартная точка входа
if __name__ == "__main__":
    raise SystemExit(main())