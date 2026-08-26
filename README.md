# FitIntel Pro v3.5

ERP/CRM система управления фитнес-клубом — FastAPI + PostgreSQL + Redis + PyQt6 тонкий клиент.

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/Kant84/fitintel-pro.git
cd fitintel-pro

# 2. Python 3.11+, виртуальное окружение
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. PostgreSQL + Redis
docker compose up -d db redis

# 4. Миграции + seed
alembic upgrade head
python scripts/create_admin.py

# 5. Запуск
uvicorn app.main:app --host 0.0.0.0 --port 8001
# Swagger: http://localhost:8001/docs
```

## Модули (E1–E58)

| Модуль | Эндпоинты | Описание |
|--------|-----------|----------|
| E1–E6 | Основа | Клиенты, абонементы, тарифы, визиты, расписание |
| E7 | Backup | Автобэкап PostgreSQL (03:00, ротация 30д) |
| E8 | Security | `.env` в `.gitignore`, ротация секретов |
| E9 | Monitoring | Health-check (БД, диск, память, бэкап) |
| E11–E15 | Платежи, Face ID, MAX Bot, SMTP, Устройства |
| E16 | Аналитика | Дашборд, KPI, прогнозы, heatmap |
| E17 | Уведомления | Email/SMS/WebPush/MAX, дайджест |
| E18 | Коммерция | White-label, тенанты, брендинг |
| E19 | Экспорт | xlsx/csv/json/xml, JWT-ссылки, GDPR ZIP |
| E20 | Бухгалтерия | ПКО/РКО, ОСВ, P&L, баланс, 1С-обмен |
| E21 | A&A интеграция | Импорт/экспорт CSV, webhook, журнал |
| E22 | 1С Fitness | Заготовка CommerceML |
| E26 | YooKassa | Платежи, рекурренты, возвраты |
| E28–E30 | Лицензия, Phone Verify, Setup Master |
| E31–E33 | Фискализация, 1С, Документы (PDF/DOCX/ЭП) |
| E34–E41 | Маркетинг, Терминал, Рефералы, Корпоратив, Сезонные кампании, Нишевые шаблоны, Booking Widget |
| E42–E48 | Documents bulk, Feature Flags, AI Analytics, Video AI, MAX Bot FSM, DAL, Отчётность |
| E50–E52 | HA, UI-Config, Тонкий клиент |
| E55–E58 | Платежи/Face ID, MAX/Интеграции, Рассылки, Оповещения |

## Тонкий клиент (PyQt6)

```bash
cd fitintel-desktop
python main.py
```

## Логи

```
logs/app.log      # Все логи (ротация 10MB×5)
logs/error.log    # WARNING+ (ротация 10MB×3)
logs/access.log   # HTTP-запросы
```

## Документация

- `PROD_NOTES.md` — полная документация по развёртыванию (E1–E58)
- `doc/` — шпаргалки по ролям, архитектура
- `deploy/` — Terraform, Ansible, Docker, monitoring

## Лицензия

FitIntel Pro | Проприетарное ПО
