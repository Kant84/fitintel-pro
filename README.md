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

## Модули (132 эндпоинта)

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
| Health | 1 | Проверка состояния |

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
