# FitIntel Pro

**ERP/CRM система управления фитнес-клубом** — FastAPI + PostgreSQL + Redis.

## Быстрый старт

```bash
# 1. Клонировать
https://github.com/Kant84/fitintel-pro.git
cd fitintel-pro

# 2. Python 3.12+, виртуальное окружение
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Запустить PostgreSQL + Redis
docker compose up -d db redis

# 4. Миграции + seed
alembic upgrade head
make seed

# 5. Запуск
make run
# Swagger: http://localhost:8000/docs
```

## Модули (168 эндпоинтов)

| Модуль | Эндпоинты | Описание |
|---|---|---|
| Auth | 7 | JWT логин, OAuth2, RBAC проверки |
| Users | 14 | CRUD, роли, пароли |
| Clients | 5 | CRM клиенты |
| Tariffs | 5 | Тарифные планы |
| Subscriptions | 8 | Абонементы + freeze/renew/cancel |
| Visits | 13 | Вход/выход, статистика |
| Access Control | 21 | QR/RFID, турникеты, шкафчики |
| Finance | 24 | Кошелёк, платежи, чеки, касса, продажи |
| RBAC | 12 | Роли, разрешения, матрица доступа |
| Devices | 5 | Управление СКУД-устройствами |
| Hardware | 11 | Hardware Abstraction Layer (любой СКУД) |
| Analytics | 4 | Дашборд, посещения, финансы, retention |
| Self-Service | 3 | Личный кабинет клиента |
| Documents | 4 | Шаблоны, генерация, скачивание |
| Marketing | 4 | Кампании, сегменты, SMS |
| Gamification | 2 | Уровни, достижения |
| Online Training | 3 | Онлайн-тренировки |
| Health | 1 | Проверка состояния |

## Hardware Abstraction Layer (универсальная система СКУД)

Поддержка **любых** СКУД-устройств через YAML-конфиг:

| Драйвер | Производитель | Модели | Протокол |
|---|---|---|---|
| `EraDriver` | ЭРА | T-1000, T-2000, C-100, C-PRO, T-UNI | TCP |
| `X1Driver` | X1 | X1-LITE, X1-PRO, X1-MAX, X1-NET | HTTP API + WebSocket |
| `KerongDriver` | Kerong | KR-S50, KR-M24, KR-M40, KR-PRO | Modbus RTU/TCP |
| `GenericModbusDriver` | Любой | MODBUS-TCP, MODBUS-RTU | Modbus |
| `GenericHttpDriver` | Любой | HTTP-API | REST API |
| `GenericMqttDriver` | Любой | MQTT | MQTT |

Добавить новое устройство — просто отредактируй `config/devices.yaml` без изменения кода!

## Frontend (React + TypeScript + Tailwind)

```powershell
# Установка фронтенда (Windows PowerShell)
.\install-frontend.ps1
# или вручную: cd frontend && npm install && npm run dev
```

| Раздел | Страницы |
|---|---|
| **Админ-панель** | Дашборд, Клиенты, Абонементы, Посещения, Финансы, Доступ, Устройства, Аналитика, Настройки |
| **Клиентский кабинет** | Профиль, Мои абонементы, Мои посещения, Кошелёк |

## Инфраструктура

```
deploy/
  terraform/          # Yandex Cloud (VPC, VMs, ALB)
  ansible/            # Настройка серверов
  monitoring/         # Prometheus + Grafana + Zabbix
  docker-compose.*.yml
Dockerfile
.gitlab-ci.yml        # CI/CD: lint → test → build → deploy
Makefile
scripts/
  setup.sh            # Быстрая настройка окружения
  install-frontend.ps1 # Установка фронтенда (Windows)
```

## Команды

```bash
make install   # Установка зависимостей
make migrate   # Применить миграции
make seed      # Заполнить роли и разрешения
make run       # Запуск dev-сервера
make test      # Запуск тестов
make lint      # Проверка кода
make docker-up # PostgreSQL + Redis в Docker
```

## Роли по умолчанию

`owner`, `admin`, `manager`, `trainer`, `cashier`, `accountor`, `support`, `client`, `device`

## Переменные окружения

См. `.env.example`

## Лицензия

FixIntel | Проприетарное ПО
