# FitIntel Pro

Система управления фитнес-клубом: сервер (FastAPI + PostgreSQL + Redis/Celery) + desktop-клиент (PyQt6) + кассовый модуль (54-ФЗ, АТОЛ ДТО 10) + AI-аналитика оттока + SKUD/RFID/Face ID + мессенджеры (MAX/Telegram).

**Текущий релиз: v1.5.3** — состав, платформы, SHA256: [RELEASES.md](RELEASES.md).

## Состав системы

| Компонент | Технологии | Где |
|---|---|---|
| Сервер API | Python 3.11, FastAPI, SQLAlchemy, PostgreSQL 16, Redis, Celery | `app/` |
| Desktop-клиент | Python 3.11, PyQt6 | `fitintel-desktop/` |
| Касса/фискализация | HTTP ДТО 10 (АТОЛ), адаптеры Штрих-М/Эвотор/Меркурий, mock | `app/api/v1/fiscal.py`, `app/services/fiscal/` |
| Эквайринг | Сбер (DLL/JSON), Тинькофф, Райффайзен; mock | `app/services/bank/` |
| Онлайн-оплаты | ЮKassa (webhook, возвраты, автосписания), СБП (mock) | `app/api/v1/yookassa.py` |
| Бухгалтерия | проводки в PostgreSQL (`accounting_entries`) + внутренняя SQLite-учётка + 1С CommerceML 2.0 | `app/services/accounting/` |
| AI-модуль оттока | scikit-learn (logreg), самообучение + сверка | `app/api/v1/ai_engine.py`, `analytics_ai.py` |
| Доступ в клуб | RFID/QR/динамические QR/Face ID (dlib), SKUD ITC, Kerong, шкафчики | `app/api/v1/{visits,credentials,lockers,face_id,dynamic_qr,skud_itconnect,kerong}.py` |
| Коммуникации | MAX (бот + FSM + чаты WS), Telegram, email/SMS/webpush | `app/api/v1/{messenger,max_bot,max_bot_fsm,telegram,notifications,chat,chats}.py` |
| Развёртывание | Docker Compose: nginx + api + celery + redis + db | `deploy/` |

## Быстрый старт (разработка)

```bash
cd deploy && docker compose -f docker-compose.test.yml up -d --build   # API: http://localhost:8001/docs
cd fitintel-desktop && python main.py
```

## Структура репозитория

```
app/api/v1/      # ~90 роутеров (auth, clients, payments, fiscal, ai_engine, ...)
app/services/    # ~55 сервисов + accounting/ bank/ fiscal/ connectors/
deploy/          # compose.test/prod, .env.example, backup/, monitoring/, nginx/
fitintel-desktop/# main.py, windows/*, api/client.py
docs/            # этот пакет
```

## Документация

| Документ | Для кого | Содержание |
|---|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | разработчики, интеграторы | компоненты, адаптеры, потоки данных, БД, RBAC, deploy-топология |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | сотрудники клуба | сценарии по ролям: касса, абонементы, доступ, тренеры, чаты |
| [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | администратор | мастер установки, роли/права/экраны, бэкапы, адаптеры, feature flags |
| [FISCAL_GUIDE.md](docs/FISCAL_GUIDE.md) | кассир, бухгалтер | смены, авто-фискализация, проводки, эквайринг, онлайн-оплаты, реготчётность |
| [API_OVERVIEW.md](docs/API_OVERVIEW.md) | разработчики, 1С-интеграторы | все группы endpoint'ов, коды ошибок, примеры |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | все | симптом → причина → решение, логи, диагностика |

## Поддержка

Desktop: Помощь → Поддержка (MAX), кнопка «Скопировать логи». Сервер: `docker compose logs api`. БД: `docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai`.
