# FITINTEL PRO — ТЕХНИЧЕСКАЯ ДОКУМЕНТАЦИЯ

**Версия документа:** 1.7.2 | **Версия приложения:** 1.6.1
**Дата:** Октябрь 2026 | **Статус:** Production Ready

---

## СОДЕРЖАНИЕ

**ЧАСТЬ 1. ОБЩИЕ СВЕДЕНИЯ**
1. Общие сведения
2. Архитектура системы
3. Технологический стек
4. Структура проекта

**ЧАСТЬ 2. ЗАВИСИМОСТИ И ДАННЫЕ**
5. Зависимости (4 файла)
6. Модели данных

**ЧАСТЬ 3. API И ДОСТУП**
7. API Reference (191 эндпоинт)
8. RBAC: Роли, права, экраны

**ЧАСТЬ 4. ОБОРУДОВАНИЕ И СЕРВИСЫ**
9. Hardware Abstraction Layer (HAL)
10. Ключевые сервисы
11. Музыкальный модуль (DJ-агент)

**ЧАСТЬ 5. ИНФРАСТРУКТУРА**
12. Инфраструктура и развёртывание
13. Команды администрирования
14. Безопасность
15. Интеграции
16. Мониторинг, логи, бэкапы

**ЧАСТЬ 6. ДИАГНОСТИКА И ПРИЛОЖЕНИЯ**
17. Устранение неполадок
18. Приложения

---

# ЧАСТЬ 1. ОБЩИЕ СВЕДЕНИЯ

## 1. ОБЩИЕ СВЕДЕНИЯ

**FitIntel Pro** — комплексная ERP/CRM-система управления фитнес-клубом. Полный цикл: регистрация клиентов, продажа абонементов, контроль доступа (СКУД), касса (54-ФЗ), AI-аналитика, коммуникации (MAX/Telegram), музыкальный пульт.

### 1.1. Ключевые характеристики

| Параметр | Значение |
|---|---|
| Версия приложения | 1.6.1 |
| Версия документа | 1.7.2 |
| Язык разработки | Python 3.11–3.12 |
| Веб-фреймворк | FastAPI 0.137.1 |
| База данных | PostgreSQL 16 |
| Кэш / Брокер | Redis 7 |
| ORM | SQLAlchemy 2.0.51 |
| Миграции | Alembic 1.18.4 |
| API эндпоинтов | ~191+ (по openapi.json) |
| SQLAlchemy моделей | ~50 |
| Pydantic схем | 121 |
| Сервисов | ~55 |
| Репозиториев | 22 |
| Hardware драйверов | 7 (в PDF v1.1 — 6) |
| Ролей RBAC | 9 |
| Разрешений (permissions) | 51 |
| Уровней геймификации | 50 |
| Строк кода | ~30 000 |
| Файлов зависимостей | 3 основных + 1 опциональный |
| **Вкладок в desktop sidebar** | **17** |
| **Подвкладок первого уровня** | **63** |
| **Подвкладок второго уровня** | **8** |
| **Отдельных окон (диалоги)** | **11** |
| **Всего уникальных экранов desktop** | **~99 (расчётно)** |

### 1.2. Модель поставки

| Компонент | Где | Формат |
|---|---|---|
| Сервер API | `app/` | Docker-образ `fitintel:prod` |
| Desktop-клиент | `fitintel-desktop/` | `FitIntelDesktop-Setup_v1.6.1.exe` (Inno Setup, onefile, ~154 МБ) |
| React-админка | `app/src/` | Vite-сборка (опционально) |
| PWA для тренеров | `app/static/trainer-pwa/` | Отдельный веб-интерфейс |
| Лицензия | FIPRO-ключ | Ed25519, привязка к machine-id |
| DJ-агент | `scripts/music/` | Внутри desktop-сборки |

### 1.3. Два типа музыкальных зон

| Тип | Описание | Что работает |
|---|---|---|
| `local_agent` | Плеер на этом ПК (mpv) | Полный пульт: деки, EQ, пады, авто-микс |
| `external` | Коробка провайдера (Muzuka, Trison) | Команды play/pause/volume/energize по HTTP |

### 1.4. Структура desktop: 17 вкладок sidebar

В главном окне desktop слева — **фиксированный список из 17 вкладок**:

| # | Название | Код | Иконка |
|---|---|---|---|
| 1 | Главная | dashboard | домик |
| 2 | Музыка/DJ | music | нота |
| 3 | Клиенты | clients | люди |
| 4 | Входы/Выходы | visits | дверь |
| 5 | Абонементы | subscriptions | карта |
| 6 | Услуги | services | гантели |
| 7 | Расписание | schedule | календарь |
| 8 | Бухгалтерия | accounting | книга |
| 9 | MAX сообщения | messenger | конверт |
| 10 | Уведомления | notifications | колокольчик |
| 11 | AI центр | ai_center | круг |
| 12 | Пользователи | users | профиль |
| 13 | История | audit | линии |
| 14 | Face ID | face_id | лицо |
| 15 | Настройки | settings | шестерёнка |
| 16 | Браслеты/Карты | credentials | ключ |
| 17 | Подключения | connections | диск |

### 1.5. Хабы и подвкладки

Три вкладки sidebar — это **хабы** с горизонтальными подвкладками:

| Хаб | Подвкладок |
|---|---|
| **Финансы** (открывается через вкладку «Бухгалтерия») | 6: Платежи, Бухгалтерия, Отчёты, Документы, Тарифы, Экспорт |
| **Настройки** | 9: Настройки, Мастер установки, Экраны ролей, Лицензия, Устройства, Параметры клуба, Роли и права, Интеграции, Коммерция |
| **AI центр** | 2: AI Центр, Аналитика |

**Все подвкладки первого уровня (63):**

| Вкладка/Хаб | Подвкладки | Кол-во |
|---|---|---|
| Главная | Обзор, Прогноз, Тепловая карта, AI Отток | 4 |
| Финансы (хаб) | Платежи, Бухгалтерия, Отчёты, Документы, Тарифы, Экспорт | 6 |
| Платежи | Платежи клиента, Проводки (бухгалтерия) | 2 |
| Бухгалтерия | Касса, Отчёты, Проводки, 1С | 4 |
| MAX сообщения | Чаты, Рассылка, Привязки, Напоминания, Журнал, Отзывы, Новости | 7 |
| Уведомления | Email, SMS, Web Push, Отправка, Журнал | 5 |
| Настройки (хаб) | Настройки, Мастер установки, Экраны ролей, Лицензия, Устройства, Параметры клуба, Роли и права, Интеграции, Коммерция | 9 |
| Параметры клуба | Временные параметры, Лейблы бота, Настройки приложения, Бонусы | 4 |
| Интеграции | A&A, 1C Fitness, Внешние системы | 3 |
| A&A (внутри Интеграций) | Импорт CSV, Экспорт, Журнал, Webhook | 4 |
| Коммерция | White-label, Тенанты | 2 |
| AI центр (хаб) | AI Центр, Аналитика | 2 |
| Услуги | Услуги, Магазин | 2 |
| Расписание | Занятия по дням, Тренеры, Записи | 3 |
| Браслеты/Карты | Клиентская карта, Программирование замков, Онлайн-замки | 3 |
| Экспорт (внутри Финансов) | Экспорт, Право на забвение, Журнал | 3 |

**Все подвкладки второго уровня (8):**

| Родитель | Подвкладки |
|---|---|
| Параметры клуба | Временные параметры, Лейблы бота, Настройки приложения, Бонусы |
| A&A (внутри Интеграций) | Импорт CSV, Экспорт, Журнал, Webhook |

### 1.6. Что видит конкретная роль

> ⚠️ **Таблица ниже — модель по скринам superadmin, а не выгрузка из БД.**
> Реальная матрица — в `ui_role_screens`. Проверить:
> ```sql
> SELECT r.code, COUNT(*) FILTER (WHERE urs.visible) AS visible
> FROM roles r
> LEFT JOIN ui_role_screens urs ON urs.role_id = r.id
> GROUP BY r.code ORDER BY r.code;
> ```

Не все 17 вкладок видны каждой роли. Модель:

| Роль | Вкладок | Какие |
|---|---|---|
| **superadmin** | 17 | Все |
| **admin** | 16 | Все, кроме «Подключения» |
| **manager** | 12 | Главная, Музыка, Клиенты, Входы, Абонементы, Услуги, Расписание, Бухгалтерия, MAX, Уведомления, AI центр, Настройки |
| **cashier** | 8 | Клиенты, Входы, Абонементы, Бухгалтерия (только Платежи), Расписание, Настройки, Face ID, Браслеты |
| **trainer** | 5 | Главная, Клиенты, Входы, Расписание, Настройки |
| **reception** | 5 | Клиенты, Входы, Face ID, Браслеты, Настройки |
| **accountant** | 6 | Главная, Бухгалтерия, Отчёты, Экспорт, Настройки, Уведомления |
| **client** | 1–3 | Личный кабинет (заготовка) |
| **device** | 1 | СКУД API (без UI) |

**Строгая модель:** не отмеченный в `ui_role_screens` экран — не виден вообще.

---

## 2. АРХИТЕКТУРА СИСТЕМЫ

### 2.1. Общая схема (прод)

```
┌─────────────────────────────────────────────────────────────────┐
│                         КЛИЕНТЫ                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Desktop      │  │ Боты MAX/    │  │ СКУД (турникеты,     │  │
│  │ (PyQt6)      │  │ Telegram     │  │ RFID, камеры)        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
          └────────────┬────┴─────────────────────┘
                       ↓
          ┌────────────────────────┐
          │  nginx:80/443 (TLS)    │
          │  rate-limit: API 10r/s │
          │             auth 5/min │
          └───────────┬────────────┘
                      ↓
          ┌────────────────────────┐
          │  api (FastAPI)         │
          │  fitintel:prod         │
          │  uvicorn 4 workers     │
          └───┬────────────────┬───┘
              │                │
              ↓                ↓
      ┌──────────────┐  ┌──────────────┐
      │ postgres:16  │  │ redis:7      │
      │ (volume)     │  │ (allkeys-lru)│
      └──────────────┘  └──────┬───────┘
                               ↓
                        ┌──────────────┐
                        │celery-worker │
                        └──────────────┘

Мониторинг (отдельный compose):
Prometheus + Grafana + Loki + Promtail + node-exporter + cAdvisor + Alertmanager
```

### 2.2. Слойная архитектура (Clean Architecture)

```
┌──────────────────────────────────────────────────────┐
│           PRESENTATION LAYER                          │
│  Admin Panel (PyQt6) │ Client Cabinet │ Swagger Docs │
├──────────────────────────────────────────────────────┤
│           API LAYER (FastAPI)                         │
│  Routers │ Schemas (Pydantic) │ Middleware │ RBAC    │
├──────────────────────────────────────────────────────┤
│           SERVICE LAYER                               │
│  Services (~55) │ HAL (Drivers) │ Tasks (Celery)     │
│  Notifications (Email/SMS/Push)                      │
├──────────────────────────────────────────────────────┤
│           DATA LAYER                                  │
│  Repositories (22) │ Models (SQLAlchemy) │ Alembic   │
├──────────────────────────────────────────────────────┤
│           INFRASTRUCTURE                              │
│  Redis │ Docker │ Nginx+SSL │ Prometheus/Grafana    │
└──────────────────────────────────────────────────────┘
```

**Поток запроса:** `Client → Nginx → FastAPI Router → Service → Repository → PostgreSQL`

---

## 3. ТЕХНОЛОГИЧЕСКИЙ СТЕК

### 3.1. Backend

| Компонент | Версия | Назначение |
|---|---|---|
| FastAPI | 0.137.1 | ASGI веб-фреймворк, OpenAPI/Swagger |
| Uvicorn | 0.49.0 | ASGI сервер |
| SQLAlchemy | 2.0.51 | ORM |
| psycopg | 3.3.4 | PostgreSQL драйвер |
| Pydantic | 2.13.4 | Валидация, сериализация |
| PyJWT | 2.13.0 | JWT токены |
| passlib + bcrypt | 1.7.4 / 5.0.0 | Хеширование паролей |
| Celery | 5.6.3 | Асинхронные задачи |
| redis-py | 6.4.0 | Кэш, брокер |
| Alembic | 1.18.4 | Миграции БД |
| APScheduler | 3.11.2 | Планировщик (аналитика 00:05) |
| ReportLab | 4.5.1 | PDF документы |
| qrcode | 8.2 | QR-пропуска |
| scikit-learn | latest | AI-модель оттока |
| dlib / face_recognition | 20.0.1 / 1.3.0 | Face ID (ResNet-34, 128 эмбеддинг) |
| xgboost | latest | Gradient boosting (опционально) |
| pyarrow | latest | Feature store (опционально) |

### 3.2. Frontend (Desktop)

| Компонент | Версия | Назначение |
|---|---|---|
| PyQt6 | 6.6+ | UI фреймворк |
| requests | 2.31+ | HTTP клиент |
| opencv-python | 4.8+ | Face ID (камера) |
| PyInstaller | 6.0+ | Сборка .exe |
| matplotlib | 3.8+ | Графики (опционально) |
| pyscard | 2.0+ | RFID (PC/SC) — опционально |

### 3.3. Frontend (React, опционально)

| Компонент | Версия | Назначение |
|---|---|---|
| React | 18 | UI (админ-панель) |
| TypeScript | 5.4+ | Типизация |
| Vite | 5+ | Сборщик |
| Tailwind CSS | 3.4 | Стили |
| shadcn/ui | latest | 60+ компонентов |

### 3.4. Инфраструктура

| Компонент | Версия | Назначение |
|---|---|---|
| PostgreSQL | 16 | Основное хранилище |
| Redis | 7 | Кэш, брокер, сессии |
| Nginx | 1.25+ | Reverse proxy, TLS, rate-limit |
| Docker | 24+ | Контейнеризация |
| Prometheus | 2.51 | Сбор метрик |
| Grafana | 10.4 | Дашборды |
| Loki + Promtail | latest | Логи |
| Alertmanager | latest | Алерты |
| mpv | v0.41+ | Плеер для музыки (в комплекте) |
| NSSM | 2.24-101 | Служба Windows (в комплекте) |

---

## 4. СТРУКТУРА ПРОЕКТА

### 4.1. Backend (`app/`)

```
app/
├── main.py                      # Точка входа, ~60 роутеров
├── main_debug.py                # Отладочная точка входа
├── info.md                      # Заметки разработчика
├── .gitignore, .license_key, .license_state
│
├── components.json              # React: shadcn
├── eslint.config.js             # React: ESLint
├── index.html                   # React: entry
├── package.json, package-lock.json
├── postcss.config.js, tailwind.config.js
├── tsconfig.json, tsconfig.app.json, tsconfig.node.json
├── vite.config.ts
│
├── api/
│   ├── dependencies.py
│   └── v1/                      # ~90 роутеров
│       ├── __init__.py
│       ├── aa_bridge.py, access.py, access_cache.py, access_control.py
│       ├── ai_engine.py, analytics.py, analytics_ai.py
│       ├── analytics_chart.py, analytics_dashboard.py
│       ├── audit.py, auth.py, auth_debug.py, auto.py
│       ├── bank_online.py, booking_widget.py, branding.py
│       ├── cash_desk.py, chat.py, chats.py
│       ├── clients.py, client_history.py, client_verification.py
│       ├── club_params.py, commercial.py, connectors.py, corporate.py
│       ├── credentials.py, dal.py, devices.py
│       ├── documents.py, documents_bulk.py, document_templates.py
│       ├── dynamic_qr.py, equipment.py
│       ├── exports.py, export_api.py
│       ├── face_id.py, feature_flags.py, feature_flags_adv.py, fiscal.py
│       ├── gamification.py, hardware.py, health.py, health_extended.py
│       ├── integrations.py, integrations_config.py
│       ├── kerong.py, license_api.py, lockers.py
│       ├── marketing.py, max_bot.py, max_bot_fsm.py, messenger.py
│       ├── miniapp_config.py, ml.py, niche.py
│       ├── notifications.py, online_sessions.py, online_training.py
│       ├── ops.py, payments.py, permissions.py
│       ├── phone_verify.py, print.py
│       ├── rbac.py, reader.py, receipts.py, recurring.py
│       ├── referrals.py, reporting.py, reports_ops.py
│       ├── rfid_reader.py, roles.py, sales.py, seasonal.py
│       ├── selfservice.py, self_learning.py, server_settings.py
│       ├── services.py, setup.py, shop.py, skud_itconnect.py
│       ├── sse.py, subscriptions.py, subscription_lifecycle.py
│       ├── tariffs.py, telegram.py, trainers.py
│       ├── ui_config.py, users.py
│       ├── video_ai.py, video_alerts.py, visits.py
│       ├── wallet.py, warehouse.py, ws_alerts.py, yookassa.py
│       │
│       ├── endpoints/           # подпакет
│       │   ├── accounting.py
│       │   └── fiscal.py
│       │
│       └── music/               # подпакет (модуль музыки)
│           ├── __init__.py
│           ├── agent.py         # /music/agent/state, /register, /pads
│           ├── deps.py
│           ├── dj.py            # POST /zones/{id}/dj
│           ├── zones.py         # CRUD зон
│           ├── playlists.py     # CRUD плейлистов
│           ├── schedule.py      # расписание фоновой музыки
│           ├── sfx.py           # пады (CRUD сэмплов)
│           └── license.py       # лицензия фоновой музыки
│
├── core/
│   ├── config.py, constants.py, exceptions.py
│   ├── license_guard.py, license_public.pem
│   ├── logger.py, logging.py
│   ├── qr.py, security.py
│
├── db/
│   ├── base.py, session.py
│   └── seed/
│       ├── apply_hotfix.py, full_seeder.py
│       ├── run_seed.py, seed_admin.py
│       ├── seed_permissions.py, seed_roles.py
│
├── dto/__init__.py              # пустой пакет (задел)
│
├── models/                      # ~50 SQLAlchemy моделей
│   ├── access.py, access_cache.py, access_log.py
│   ├── analytics.py, audit.py
│   ├── cash_desk_session.py, cash_operation.py
│   ├── chat.py, client.py, client_event.py
│   ├── commercial.py, credential.py
│   ├── device.py, discount.py, document.py, dynamic_qr.py
│   ├── equipment.py, export.py, external_sync_log.py
│   ├── face_id.py, feature_flag.py
│   ├── gamification_level.py, hall.py
│   ├── hardware_device.py, integration.py
│   ├── locker.py, locker_privilege.py, locker_session.py
│   ├── marketing_campaign.py, marketing_trigger.py
│   ├── max_bot.py, notification.py, online_session.py
│   ├── payment.py, permission.py, product.py
│   ├── receipt.py, role.py, role_permission.py
│   ├── sale.py, service.py, subscription.py, subscription_event.py
│   ├── tariff.py, telegram.py, trainer.py
│   ├── user.py, user_role.py, video_alert.py
│   ├── visit.py, wallet.py, wallet_transaction.py
│   ├── warehouse.py, yookassa.py
│   └── __init__.py
│
├── repositories/                # ~22 репозитория
│   ├── access_cache_repository.py, access_log_repository.py, access_repository.py
│   ├── cash_desk_repository.py, client_event_repository.py, client_repository.py
│   ├── credential_repository.py, device_repository.py, document_repository.py
│   ├── external_sync_repository.py, locker_privilege_repository.py
│   ├── locker_repository.py, locker_session_repository.py
│   ├── payment_repository.py, receipt_repository.py
│   ├── role_repository.py, subscription_repository.py, tariff_repository.py
│   ├── user_repository.py, visit_repository.py, wallet_repository.py
│   └── __init__.py
│
├── routers/                     # отдельные роутеры (вне v1)
│   ├── face_id.py
│   ├── license.py
│   └── __init__.py
│
├── schemas/                     # Pydantic-схемы
│   ├── access.py, access_cache.py, access_log.py
│   ├── analytics.py, auth.py, cash_desk.py
│   ├── client.py, client_event.py, credential.py
│   ├── device.py, document.py, dynamic_qr.py
│   ├── enums.py, face_id.py, feature_flag.py
│   ├── locker.py, locker_privilege.py, locker_session.py
│   ├── payment.py, permission.py, rbac.py
│   ├── receipt.py, report.py, role.py, role_permission.py
│   ├── sale.py, sale_temp.py, service.py
│   ├── subscription.py, subscription_event.py
│   ├── tariff.py, trainer.py, user.py, user_role.py
│   ├── video_alert.py, visit.py, wallet.py
│   └── __init__.py
│
├── services/                    # ~55 сервисов
│   ├── access_cache_service.py, access_service.py, analytics_service.py
│   ├── audit_service.py, auth_service.py, booking_sweep.py
│   ├── bot_keyboards.py, bot_scenarios.py
│   ├── cash_desk_service.py, chat_service.py
│   ├── client_history_service.py, client_service.py
│   ├── commercial_service.py, credential_service.py
│   ├── device_protocols.py, device_service.py, document_service.py
│   ├── email_queue_service.py, email_service.py, entry_policy.py
│   ├── export_service.py, face_id_service.py, fiscal_service.py
│   ├── gamification_service.py, integration_service.py
│   ├── license_service.py, locker_service.py, marketing_service.py
│   ├── notification_service.py, offline_sync_service.py
│   ├── online_training_service.py, payment_service.py
│   ├── print_service.py, qr_service.py
│   ├── rbac_guard.py, rbac_service.py
│   ├── receipt_service.py, report_service.py
│   ├── role_permission_service.py, role_service.py
│   ├── sale_service.py, sbp_service.py, scheduler_service.py
│   ├── shop_service.py, subscription_lifecycle_service.py
│   ├── subscription_service.py, tariff_service.py
│   ├── telegram_bot_service.py, terminal_emulator.py
│   ├── trainer_service.py, user_role_service.py, user_service.py
│   ├── visit_service.py, wallet_service.py, yookassa_service.py
│   │
│   ├── accounting/
│   │   ├── internal_accounting.py, onec_integration.py, __init__.py
│   ├── bank/
│   │   ├── universal_bank.py, __init__.py
│   ├── connectors/
│   │   ├── base.py, fitness1c.py, sync_engine.py, __init__.py
│   └── fiscal/
│       ├── universal_fiscal.py, __init__.py
│
├── hardware/                    # HAL
│   ├── base.py, manager.py, registry.py, rfid_reader.py
│   ├── __init__.py
│   └── drivers/
│       ├── acs_acr1252u.py
│       ├── era.py, x1.py, kerong.py
│       ├── generic_http.py, generic_modbus.py, generic_mqtt.py
│       └── __init__.py
│
├── integrations/
│   ├── __init__.py
│   ├── max/
│   │   ├── service.py, verification.py, __init__.py
│   ├── email/, sms/, telegram/, one_c/, payments/, devices/, webhooks/
│
├── middleware/
│   ├── license_middleware.py, __init__.py
│
├── ml/
│   ├── adaptive_ui.py, auto_scheduler.py, churn_model.py
│   ├── event_logger.py, feature_store.py, pricing_engine.py
│   ├── self_heal.py, send_time_optimizer.py
│   └── __init__.py
│
├── tasks/                       # Celery-задачи
│   ├── access_control.py, analytics.py, cleanup.py
│   ├── finance.py, ml.py, notifications.py, notifications_max.py
│   ├── sync_lockers.py, sync_one_c.py, sync_skud.py, visits.py
│   └── __init__.py
│
├── templates/__init__.py        # пустой пакет (задел)
│
├── utils/
│   ├── datetime.py, pagination.py, qr.py, validators.py
│   └── __init__.py
│
├── static/
│   └── trainer-pwa/             # PWA для тренеров (отдельный интерфейс)
│       ├── index.html, manifest.json, sw.js
│       ├── icon-192.png, icon-512.png
│       └── *.jpg (фото)
│
└── src/                         # React-админка (Vite, опционально)
    ├── App.tsx, main.tsx, index.css, App.css
    ├── components/ui/           # shadcn/ui (60+ компонентов)
    ├── hooks/use-mobile.ts
    ├── layouts/AdminLayout.tsx, ClientLayout.tsx
    ├── pages/
    │   ├── Home.tsx
    │   ├── admin/               # 9 страниц
    │   │   ├── AccessPage.tsx, AnalyticsPage.tsx
    │   │   ├── ClientsPage.tsx, DashboardPage.tsx
    │   │   ├── DevicesPage.tsx, FinancePage.tsx
    │   │   ├── SettingsPage.tsx, SubscriptionsPage.tsx
    │   │   └── VisitsPage.tsx
    │   ├── auth/LoginPage.tsx
    │   └── client/              # 4 страницы
    │       ├── ClientSubscriptionsPage.tsx
    │       ├── ClientVisitsPage.tsx
    │       ├── ClientWalletPage.tsx
    │       └── ProfilePage.tsx
    └── store/authStore.ts
```

**Важно:**
- `app/src/` — отдельный React-проект, собирается через Vite → статика.
- `app/static/trainer-pwa/` — **отдельная PWA** (мобильный веб для тренеров, не входит в desktop).
- `app/api/v1/music/` — модуль управления музыкой (9 файлов).
- `app/routers/` — отдельные роутеры (`license.py`, `face_id.py`), подключаются в `main.py`.
- `app/dto/`, `app/templates/` — пустые пакеты (заделы под будущее).
- `app/api/v1/miniapp_config.py` — API для **мини-приложения MAX** (вход без пароля, кошелёк, запись).
- `main_debug.py` — отладочная точка входа (запуск с доп. логированием).
- `info.md` — заметки разработчика.

### 4.2. Desktop (`fitintel-desktop/`)

```
fitintel-desktop/
├── main.py                      # Точка входа
├── paths.py                     # SETTINGS = APP_DIR / "client_settings.json"
├── app_logging.py               # logs/client_YYYYMMDD.log
├── build.py, build_exe.bat
├── FitIntelDesktop.spec         # PyInstaller spec (АКТУАЛЬНЫЙ)
├── FitIntelPro.spec             # Устаревший (удалить)
├── installer.iss                # Inno Setup
├── rfid_monitor_widget.py       # RFID-плашка (плавающее окно)
├── test_write_card.py           # Тест записи карты
├── measure_startup.ps1, restart_desktop.ps1
├── README.md                    # Документация desktop
├── requirements-desktop.txt     # Зависимости desktop
├── FitIntel AI.code-workspace   # VS Code workspace
├── .gitignore                   # Игнор
├── build.log                    # Лог последней сборки
│
├── api/
│   ├── __init__.py
│   └── client.py                # HTTP-клиент + E55-методы
│
├── rfid/                        # RFID-операции (PC/SC)
│   ├── __init__.py
│   ├── direct_reader.py
│   ├── card_ops.py
│   ├── client_search.py
│   ├── api_ops.py
│   └── constants.py
│
├── windows/                     # ~60 экранов/виджетов
│   ├── __init__.py
│   ├── theme.py, icons.py, form_dialog.py, help_dialog.py
│   ├── print_helper.py, chart_widget.py, hub_base.py
│   ├── startup_dialog.py, activation_dialog.py
│   ├── login_window.py, main_window.py
│   ├── change_password_dialog.py, change_password_self_dialog.py
│   │
│   ├── aa_integration_tab.py, accounting_tab.py
│   ├── ai_center_tab.py, ai_hub_tab.py, analytics_tab.py
│   ├── audit_tab.py, clients_tab.py, clock_board.py
│   ├── club_params_tab.py, commerce_tab.py
│   ├── connections_tab.py, connectors_tab.py
│   ├── credentials_tab.py, dashboard_tab.py
│   ├── devices_tab.py, documents_tab.py
│   ├── export_tab.py, face_id_tab.py
│   ├── finance_hub_tab.py, integrations_tab.py
│   ├── license_tab.py, messenger_tab.py, music_tab.py
│   ├── notifications_tab.py, payments_tab.py
│   ├── reports_tab.py, roles_tab.py, schedule_tab.py
│   ├── services_settings_tab.py, services_tab.py
│   ├── settings_hub_tab.py, settings_tab.py
│   ├── setup_tab.py, shop_tab.py
│   ├── subscriptions_tab.py, tariffs_tab.py
│   ├── ui_config_tab.py, users_tab.py, visits_tab.py
│
├── assets/
│   ├── app_icon_512.png, app_icon_1024.png
│   ├── fitintel.ico, FitIntel_icon.ico
│   ├── fitintel_256.png, FitIntel_icon_256.png
│   ├── logo_wave.png
│   └── icons-generated/         # Кэш SVG (не в git)
│
├── client_settings.json         # Тема, шрифт, api_base, dj_agent
├── client_settings2.json        # Резервная копия
├── connections.json             # Профили подключения
├── connections2.json            # Резервная копия
├── shop_products.json, shop_sales.json, shop_settings.json
├── rfid_uid_cache.json, rfid_widget_pos.json
├── shop_photos/                 # Фото товаров (киоск)
├── logs/                        # client_YYYYMMDD.log
├── dist/                        # FitIntelDesktop.exe
├── build/                       # Промежуточные PyInstaller
└── installer_out/               # FitIntelDesktop-Setup_v1.6.1.exe
```

**Отдельные окна (11):**

| Файл | Окно |
|---|---|
| `login_window.py` | Вход |
| `main_window.py` | Главное окно |
| `activation_dialog.py` | Активация лицензии |
| `startup_dialog.py` | Выбор информационной базы |
| `change_password_dialog.py` | Смена пароля (админ) |
| `change_password_self_dialog.py` | Смена пароля (сам) |
| `form_dialog.py` | Универсальная форма |
| `help_dialog.py` | F1-инструкция |
| `clock_board.py` | Табло с часами (F11) |
| `rfid_monitor_widget.py` | RFID-плашка (всегда поверх) |
| `print_helper.py` | Печать/PDF |

**Меню (Файл / Вид / Помощь):**

**Файл:**
- Обновить (F5)
- Выход (Ctrl+Q)
- (разделитель)
- Сменить пароль…
- (разделитель)
- Табло с часами (F11)

**Вид:**
- Светлая тема
- Тёмная тема
- Табло с часами (полный экран) — F11
- (разделитель)
- Увеличить шрифт — Ctrl++
- Уменьшить шрифт — Ctrl−
- (разделитель)
- Переключить тему

**Помощь:**
- Инструкция по экрану (F1)
- Чат с клиентами (MAX)
- Поддержка разработчика (MAX)

**Статус-бар:** «Сервер подключён | FitIntel Pro v1.6.1» + кнопка «Инструкция» справа.

**Шапка:** «FitIntel Pro» слева, «superadmin | admin» и кнопка «Выход» (красная) справа.

### 4.3. Скрипты (`scripts/` в корне репо)

```
scripts/                         # В КОРНЕ репо (не в app/)
├── music/                       # DJ-агент (mpv)
│   ├── agent.py                 # Основной цикл агента v4.5
│   ├── deck.py                  # Deck (один mpv-процесс)
│   ├── duck.py                  # VoiceDucker (дакинг микрофона)
│   ├── pads.py                  # Очередь сэмплов
│   ├── skud_trigger.py          # СКУД-триггер для energize
│   └── fitintel_player_agent.py # Обёртка (CLI)
├── backup/
│   ├── backup.ps1, restore.ps1
│   ├── install_cron.sh, backup.env
├── seed_demo_data.py
├── create_admin.py
└── bootstrap_db.py
```

### 4.4. Деплой (`deploy/`)

```
deploy/
├── docker-compose.test.yml      # API + db + redis + nginx + celery
├── docker-compose.prod.yml      # Прод (готовый образ)
├── docker-compose.dev.yml       # Dev-профиль
├── env.example                  # Образец переменных
├── .env.monitoring.example      # Образец для мониторинга
├── .env                         # Реальные (не в git)
├── backup.zip                   # Архив бэкапа
│
├── nginx/                       # Reverse proxy, TLS
├── monitoring/
│   ├── docker-compose.monitoring.yml
│   ├── prometheus/              # prometheus.yml + rules/fitintel.yml
│   ├── grafana/                 # Дашборды, datasources
│   ├── loki/, promtail/
│   └── alertmanager/            # receiver "null" (заглушка!)
│
├── backup/                      # backup.ps1 + restore.ps1
├── ansible/                     # Ansible-плейбуки
├── systemd/                     # Systemd-юниты (Linux)
└── terraform/                   # Terraform (Yandex Cloud)
```

### 4.5. Корень репозитория

```
fitintel-pro/
├── .gitignore                   # mpv/, tools/nssm.exe, dist/, installer_out/, .env
├── README.md                    # Главный (навигация по docs/)
├── RELEASES.md                  # Релизы + SHA256
├── LICENSE                      # Проприетарная
├── requirements-base.txt        # Тяжёлые (dlib, ML, RFID)
├── requirements.txt             # Сервер API
├── requirements-dev.txt         # Разработка (опционально)
│
├── mpv/                         # mpv.exe (120 МБ, НЕ в git)
│   ├── mpv.exe, mpv.com, d3dcompiler_43.dll
│   └── .gitkeep
│
├── tools/
│   ├── nssm.exe                 # Service manager (НЕ в git)
│   └── .gitkeep
│
├── app/                         # Backend (FastAPI)
├── fitintel-desktop/            # Desktop (PyQt6)
├── scripts/                     # DJ-агент, бэкапы, seed
├── deploy/                      # Docker, nginx, monitoring, terraform
└── docs/                        # Документация
```

# ЧАСТЬ 2. ЗАВИСИМОСТИ И ДАННЫЕ

## 5. ЗАВИСИМОСТИ (4 ФАЙЛА)

### 5.1. Общая структура

FitIntel Pro использует **3 основных + 1 опциональный** файл зависимостей:

| Файл | Что ставит | Где |
|---|---|---|
| `requirements-base.txt` | Тяжёлые (dlib, ML, RFID) | Кэшируется в Docker |
| `requirements.txt` | Сервер API (FastAPI, БД, очереди) | `pip install` на сервере |
| `fitintel-desktop/requirements-desktop.txt` | Desktop-клиент (PyQt6) | Для сборки `.exe` |
| `requirements-dev.txt` | Разработка (тесты, линтеры) | Опционально, локально |

**Схема наследования:**

```
requirements.txt
    └── -r requirements-base.txt

fitintel-desktop/requirements-desktop.txt    (независимый)

requirements-dev.txt
    └── -r requirements.txt
```

### 5.2. `requirements-base.txt` — тяжёлые

**Реальный файл:**

```txt
dlib==20.0.1
face-recognition==1.3.0
face_recognition_models==0.3.0
numpy==2.4.6
pillow==12.2.0
scikit-learn
xgboost
pyarrow
pyscard==2.3.1
```

**Что важно:**

| Пакет | Размер | Зачем |
|---|---|---|
| `dlib==20.0.1` | ~50 МБ | Face ID (ResNet-34) |
| `face-recognition==1.3.0` | ~50 КБ | Обёртка над dlib |
| `face_recognition_models==0.3.0` | ~100 МБ | Веса модели |
| `numpy==2.4.6` | ~15 МБ | Векторы, эмбеддинги |
| `pillow==12.2.0` | ~3 МБ | Изображения |
| `scikit-learn` | ~30 МБ | AI-модель оттока |
| `xgboost` | ~10 МБ | Gradient boosting |
| `pyarrow` | ~30 МБ | Feature store |
| `pyscard==2.3.1` | ~200 КБ | RFID-ридеры |

**Итого:** ~400 МБ в venv.

**Если dlib не собирается:**

```bash
# Решение A — cmake
pip install cmake

# Решение B — готовое колесо
pip install dlib --only-binary :all:

# Решение C — не ставить, если Face ID не нужен
# закомментировать dlib в requirements-base.txt
```

### 5.3. `requirements.txt` — сервер API

**Реальный файл** (~110 пакетов). Основные группы:

```txt
-r requirements-base.txt

# === FastAPI / ASGI ===
fastapi==0.137.1
uvicorn==0.49.0
starlette==1.3.1
watchfiles==1.2.0
httptools==0.8.0
websockets==16.0
python-multipart==0.0.32

# === База данных ===
SQLAlchemy==2.0.51
alembic==1.18.4
psycopg==3.3.4
psycopg-binary==3.3.4
greenlet==3.5.2

# === Валидация ===
pydantic==2.13.4
pydantic-settings==2.14.1
pydantic_core==2.46.4
email-validator==2.3.0
annotated-types==0.7.0
typing-extensions==4.15.0

# === Аутентификация ===
PyJWT==2.13.0
python-jose==3.5.0
passlib==1.7.4
bcrypt==5.0.0
cryptography==49.0.0
ecdsa==0.19.2
rsa==4.9.1
pyasn1==0.6.3

# === Очереди / кэш ===
redis==6.4.0
celery==5.6.3
kombu==5.6.2
amqp==5.3.1
billiard==4.2.4
vine==5.1.0

# === Планировщик ===
APScheduler==3.11.2
tzdata==2026.2
tzlocal==5.4.3

# === HTTP ===
requests==2.34.2
httpx==0.28.1
aiohttp==3.14.1
urllib3==2.7.0
certifi==2026.6.17

# === Документы / отчёты ===
reportlab==4.5.1
fpdf2==2.8.7
openpyxl==3.1.5
qrcode==8.2

# === Платежи ===
yookassa==3.12.1

# === Устройства ===
pyserial==3.5
paho-mqtt==2.1.0
asyncio-mqtt==0.16.2

# === Утилиты ===
python-dotenv==1.2.2
PyYAML==6.0.3
psutil==7.2.2
netaddr==1.3.0
packaging==26.2
colorama==0.4.6
click==8.4.1

# === Логирование / мониторинг ===
sentry-sdk==2.63.0
prometheus_client==0.25.0

# === Шаблоны ===
jinja2==3.1.6
MarkupSafe==3.0.3
Mako==1.3.12

# === XML ===
defusedxml==0.7.1
et_xmlfile==2.0.0

# === Только Windows ===
pywin32==312; sys_platform == "win32"

# === Разное (транзитивные) ===
six, python-dateutil, distro, dnspython, idna, multidict, yarl,
frozenlist, propcache, attrs, aiohappyeyeballs, aiosignal, anyio
```

**Особенности:**
- `-r requirements-base.txt` — подтягивает тяжёлые.
- `setuptools<81` — в `requirements-base.txt` (для face_recognition_models).
- `pywin32` — с маркером `sys_platform == "win32"` (не ломает Linux).

### 5.4. `fitintel-desktop/requirements-desktop.txt` — desktop

**Реальный файл:**

```txt
# FitIntel Pro Desktop Dependencies
PyQt6>=6.6.0
requests>=2.31.0
opencv-python>=4.8.0  # для Face ID (веб-камера)
PyInstaller>=6.0     # для сборки .exe
```

**Опционально (если нужны в desktop):**
```txt
matplotlib>=3.8.0     # графики в dashboard
pyscard>=2.0.0        # RFID-ридер на рабочем месте
pywin32>=306          # Windows API (если что-то использует)
```

**Итого:** ~250 МБ в venv.

### 5.5. `requirements-dev.txt` — разработка (опционально)

```txt
-r requirements.txt

# === Тесты ===
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=5.0
factory-boy>=3.3

# === Линтеры ===
ruff>=0.6
flake8>=7.0
mypy>=1.11

# === Форматирование ===
black>=24.0
isort>=5.13

# === Pre-commit ===
pre-commit>=3.7
```

### 5.6. Установка зависимостей

**Сервер (Linux/Ubuntu):**

```bash
# 1. Системные зависимости
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    build-essential cmake libpq-dev \
    libgl1-mesa-glx libglib2.0-0 \
    libpcsclite-dev pcscd

# 2. Виртуальное окружение
cd ~/fitintel-pro
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Обновить pip
pip install --upgrade pip setuptools wheel

# 4. Установить базовые (долго!)
pip install -r requirements-base.txt

# 5. Установить всё остальное
pip install -r requirements.txt

# 6. Проверка
python -c "import dlib, face_recognition, fastapi, celery"
```

**Desktop (Windows):**

```powershell
cd "E:\FitNexus AI\FitIntel AI\fitintel-desktop"
python -m venv .venv-desktop
.\.venv-desktop\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-desktop.txt

# Проверка
python -c "import PyQt6, cv2, requests"
```

### 5.7. Docker (оптимизация сборки)

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential cmake libpq-dev \
    libgl1-mesa-glx libglib2.0-0 \
    libpcsclite-dev pcscd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Слой 1: тяжёлые (кэшируется надолго)
COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt

# Слой 2: остальное (меняется часто)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.8. Типичные проблемы с зависимостями

| Проблема | Причина | Решение |
|---|---|---|
| `dlib` не собирается | Нет cmake/C++ | `apt install cmake build-essential` |
| `dlib` собирается 30 мин | Компилируется из исходников | `pip install dlib --only-binary :all:` |
| `face_recognition_models` ошибка | setuptools ≥ 81 | `setuptools<81` |
| `Pillow` конфликт | Дубликат | Убрать `Pillow>=10.0` |
| `pywin32` не ставится на Linux | Windows-only | Маркер `sys_platform == "win32"` |
| `psycopg` требует libpq | Нет библиотеки | `apt install libpq-dev` |
| `opencv-python` требует libGL | Нет библиотеки | `apt install libgl1-mesa-glx` |
| `pyscard` требует pcscd | Нет демона | `apt install pcscd` |
| `No module named 'cv2'` | Не установлен | `pip install opencv-python` |
| `PyQt6` не находит Qt | Конфликт | `pip install --force-reinstall PyQt6 PyQt6-Qt6` |
| `ModuleNotFoundError: app` | Запуск не из корня | `python -m scripts.x` |
| Медленный импорт matplotlib | Первая загрузка | Норма |

### 5.9. Проверка установки

Файл `check_deps.py` в корне:

```python
"""Проверка всех зависимостей FitIntel Pro."""
import sys

CHECKS = [
    ("fastapi", "FastAPI"), ("uvicorn", "Uvicorn"),
    ("sqlalchemy", "SQLAlchemy"), ("alembic", "Alembic"),
    ("pydantic", "Pydantic"), ("jwt", "PyJWT"),
    ("passlib", "passlib"), ("bcrypt", "bcrypt"),
    ("redis", "redis-py"), ("celery", "Celery"),
    ("requests", "requests"), ("httpx", "httpx"),
    ("reportlab", "ReportLab"), ("qrcode", "qrcode"),
    ("yookassa", "yookassa"),
    ("dlib", "dlib (Face ID)"), ("face_recognition", "face_recognition"),
    ("numpy", "NumPy"), ("PIL", "Pillow"),
    ("sklearn", "scikit-learn"), ("pyscard", "pyscard (RFID)"),
    ("psycopg", "psycopg"), ("jinja2", "Jinja2"),
    ("prometheus_client", "prometheus_client"),
]

DESKTOP_CHECKS = [
    ("PyQt6", "PyQt6"), ("cv2", "opencv-python"),
]

def check(modules):
    ok, fail = [], []
    for mod, name in modules:
        try:
            __import__(mod)
            ok.append(name)
        except ImportError:
            fail.append(name)
    return ok, fail

print("=== Сервер ===")
ok, fail = check(CHECKS)
for m in ok: print(f"  [OK] {m}")
for m in fail: print(f"  [FAIL] {m}")

print("\n=== Desktop (опционально) ===")
ok, fail = check(DESKTOP_CHECKS)
for m in ok: print(f"  [OK] {m}")
for m in fail: print(f"  [нет] {m}")

sys.exit(1 if fail else 0)
```

Запуск: `python check_deps.py`

### 5.10. Чек-лист перед продом

- [ ] `pip install -r requirements.txt` работает без ошибок
- [ ] `python check_deps.py` — все OK
- [ ] `dlib` собран (или готовое колесо)
- [ ] `face_recognition_models` скачана (~100 МБ)
- [ ] `psycopg` работает с БД (`psql -c "\l"`)
- [ ] `redis` доступен (`redis-cli ping` → PONG)
- [ ] `celery` видит брокер (`celery -A app.tasks inspect ping`)
- [ ] `reportlab` генерирует PDF с кириллицей
- [ ] `yookassa` — ключи в `.env`
- [ ] Desktop: `python main.py` запускается
- [ ] Desktop: `pyinstaller FitIntelDesktop.spec` собирает exe
- [ ] Версии зафиксированы (`pip freeze > requirements.lock`)

---

## 6. МОДЕЛИ ДАННЫХ

### 6.1. ER-диаграмма (основные сущности)

```
users ──┬── user_roles ── roles ── role_permissions ── permissions
        │                                    │
        │                                    └── ui_role_screens ── ui_screens
        │
        ├── audit_logs
        └── license_state

clients ──┬── subscriptions ──── tariffs
          ├── visits
          ├── credentials (QR/RFID/CARD/BRACELET/MOBILE_KEY)
          ├── wallets ── wallet_transactions
          ├── payments ── receipts ── fiscal_receipts
          ├── documents ── document_events
          ├── face_id_records
          ├── client_events (timeline)
          ├── locker_sessions ── lockers
          ├── gamification_levels
          └── dynamic_qr_codes

music_zones ──┬── music_playlists
              ├── music_sfx (pads)
              └── music_pad_events

accounting_entries (Дт/Кт)
setup_wizard (шаги установки)
fiscal_shift, fiscal_pending, fiscal_settings
```

### 6.2. Основные таблицы

| Таблица | Назначение | Ключевые поля |
|---|---|---|
| `users` | Пользователи | id, username, email, password_hash, is_active, is_superuser, force_password_change |
| `roles` | Роли RBAC | id, code, name, is_system |
| `permissions` | Разрешения | id, code, name, module |
| `user_roles` | Связь | user_id, role_id |
| `role_permissions` | Связь | role_id, permission_id |
| `ui_screens` | Реестр экранов | id, code, name, order |
| `ui_role_screens` | Матрица экранов | role_id, screen_id, visible |
| `clients` | Клиенты | id, first_name, last_name, phone UNIQUE, email, birth_date, gender, client_category, status |
| `tariffs` | Тарифы | id, code, name, price, period_type, visits_count, is_unlimited |
| `subscriptions` | Абонементы | id, client_id, tariff_id, status, start_date, end_date, frozen_at, frozen_until |
| `subscription_events` | История | id, subscription_id, event_type |
| `visits` | Посещения | id, client_id, entry_time, exit_time, status |
| `credentials` | QR/RFID | id, client_id, type, code, is_active, valid_until |
| `lockers` / `locker_sessions` | Шкафчики | id, number, status, client_id |
| `locker_privileges` | Привилегии шкафчиков | id, client_id, locker_id |
| `wallets` | Кошельки | id, client_id, balance, frozen_balance |
| `wallet_transactions` | Транзакции | id, wallet_id, type, amount |
| `payments` | Платежи | id, client_id, amount, method, status, completed_at |
| `receipts` | Чеки | id, payment_id, receipt_number, fiscal_data, sent_to_ofd |
| `fiscal_shift` | Кассовые смены | id, opened_at, closed_at, is_open |
| `fiscal_pending` | Отложенные обороты | сумма, дата |
| `fiscal_settings` | Настройки ККТ | id, driver, dto_url, ofd |
| `accounting_entries` | Проводки | id, entry_date, debit, credit, amount, source |
| `face_id_records` | Face ID | id, client_id, face_encoding, photo_url |
| `dynamic_qr_codes` | Динамические QR | id, client_id, jti, expires_at, used_at |
| `documents` | Документы | id, type, client_id, template_id, content, status |
| `document_events` | События документа | id, document_id, event_type |
| `document_templates` | Шаблоны | id, code, name, text |
| `audit_logs` | Аудит | id, user_id, action, entity_type, entity_id, before_data, after_data |
| `license_state` | Лицензия | id, key, machine_id, tariff, expires_at, is_first_login, plan, device_limit |
| `dal_drivers` / `dal_devices` | Устройства | id, package_name, status, connection_string |
| `dal_events` | Журнал DAL | id, device_id, event_type |
| `music_zones` | Музыкальные зоны | id, name, provider_type, agent_token, machine_id, desired_state, desired_playlist_id, dj_state |
| `music_playlists` | Плейлисты | id, name, tracks (JSON), is_energize |
| `music_sfx` | Сэмплы | id, name, path, volume, sort |
| `music_pad_events` | События падов | id, zone_id, sfx_id, status |
| `email_queue` | Очередь писем | id, recipient, subject, status, attempts, next_attempt_at |
| `notification_settings` | Настройки уведомлений | id (1 строка), smtp_host, smtp_port, smtp_user, smtp_pass |
| `notification_log` | Журнал уведомлений | id, channel, recipient, status |
| `yookassa_webhook_events` | Идемпотентность | event_key UNIQUE |
| `recurring_schedules` | Рекуррентные платежи | id, client_id, interval, next_charge_at, status |
| `recurring_charges` | История списаний | id, schedule_id, status |
| `feature_flags` / `ff_rollouts` | Feature flags | id, key, is_active, rollout_percent |
| `ff_license_binds` | Привязка к лицензии | id, flag_key, license_feature |
| `referral_codes` / `referrals` | Рефералка | id, code, referrer_id, referred_id |
| `gamification_levels` | Уровни клиента | id, client_id, current_xp, level |
| `max_bot_bindings` | Привязка MAX | id, max_user_id, client_id |
| `max_bot_fsm` | Состояние FSM | id, max_user_id, state, context |
| `max_bot_settings` | Настройки бота | id (1 строка), bot_token |
| `setup_wizard` | Шаги установки | id, step, status |
| `service_bookings` | Записи на услуги | id, client_id, service_id, slot_datetime, status |
| `trainer_profiles` | Профили тренеров | id, user_id, specialization, rate, commission |
| `trainer_schedules` | Расписание тренеров | id, trainer_id, day, time_from, time_to |
| `online_sessions` | Онлайн-тренировки | id, trainer_id, title, start_at |
| `chat` / `chats` | Мессенджер | id, participants, messages |
| `integration_settings` | Настройки интеграций | id, type, base_url, login, password |
| `export_log` | Журнал выгрузок | id, data_type, format, created_at |
| `ops_backups` | История бэкапов | id, filename, size, created_at |

### 6.3. SQLite-учётка (внутренняя)

Отдельный файл `fitintel_accounting.db` — аналог 1С без 1С:
- `accounts`, `entries`, `contragents`, `items`, `balances`
- ПКО/РКО/реализация/поступление/ОСВ/P&L/баланс/ДДС/акт сверки

### 6.4. Связи между таблицами

**Ключевые связи:**

```
clients 1──* subscriptions
clients 1──* visits
clients 1──* payments
clients 1──* credentials
clients 1──* documents
clients 1──1 wallets
clients 1──1 gamification_levels
clients 1──* dynamic_qr_codes
clients 1──* face_id_records
clients 1──* locker_sessions

subscriptions *──1 tariffs
subscriptions 1──* subscription_events

payments 1──1 receipts
payments 1──* payment_refunds

users *──* roles (через user_roles)
roles *──* permissions (через role_permissions)
roles *──* ui_screens (через ui_role_screens)

music_zones 1──* music_playlists
music_zones 1──* music_pad_events
music_sfx 1──* music_pad_events
```

### 6.5. Индексы и ограничения

**UNIQUE:**
- `clients.phone`
- `users.username`, `users.email`
- `roles.code`, `permissions.code`
- `email_queue.event_key` (для yookassa_webhook_events)
- `music_zones.agent_token`, `music_zones.machine_id`
- `referral_codes.code`

**INDEX:**
- `music_zones(machine_id)` — для авто-регистрации
- `audit_logs(entity_type, entity_id)`
- `visits(client_id, entry_time)`
- `payments(client_id, status)`

**FOREIGN KEY:**
- `subscriptions.client_id → clients.id` (CASCADE)
- `subscriptions.tariff_id → tariffs.id`
- `visits.client_id → clients.id`
- `payments.client_id → clients.id`
- `documents.client_id → clients.id`
- `music_pad_events.zone_id → music_zones.id`
- `music_pad_events.sfx_id → music_sfx.id`

# ЧАСТЬ 3. API И ДОСТУП

## 7. API REFERENCE (~191+ ЭНДПОИНТ)

База: `http://<сервер>:8001/api/v1`
Авторизация: `POST /auth/login` → Bearer token

### 7.1. Auth / RBAC (22)

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/login` | Вход (JSON: login, password) |
| POST | `/auth/token` | OAuth2 (form, legacy) |
| POST | `/auth/refresh` | Обновление токена |
| GET | `/auth/me` | Текущий пользователь |
| POST | `/auth/change-password` | Смена пароля |
| GET | `/auth/token-check` | Проверка токена |
| POST | `/auth/2fa/*` | 2FA (заготовка) |
| POST | `/auth/forgot-password` | Восстановление |
| GET | `/users/` | Список (offset, limit, search) |
| GET | `/users/{id}` | По UUID |
| POST | `/users/` | Создать |
| PATCH | `/users/{id}` | Обновить |
| POST | `/users/{id}/deactivate` | Деактивировать |
| POST | `/users/{id}/reset-password` | Сброс пароля |
| POST | `/users/{id}/roles/assign\|revoke` | Назначение/снятие роли |
| GET | `/users/{id}/roles\|permissions` | Роли/права |
| GET | `/roles/` | Список ролей |
| POST | `/roles/` | Создать |
| GET | `/permissions/` | Список прав |
| GET | `/rbac/matrix` | Матрица RBAC |
| GET | `/rbac/check-access\|explain-access\|debug-access` | Диагностика |
| GET | `/rbac/health` | Health |

### 7.2. Клиенты / Абонементы / Визиты (20)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/clients/` | Список (search, filter) |
| POST | `/clients/` | Создать |
| GET/PATCH/DELETE | `/clients/{id}` | CRUD |
| GET | `/clients/{id}/timeline` | История |
| POST | `/clients/{id}/anonymize` | 152-ФЗ |
| POST | `/clients/verify-phone/request\|confirm\|status` | Телефон |
| GET/POST | `/tariffs/` | Тарифы |
| GET | `/tariffs/{code}` | По коду |
| GET/POST | `/subscriptions/` | Абонементы |
| POST | `/subscriptions/{id}/freeze\|unfreeze\|renew\|cancel` | Жизненный цикл |
| GET | `/subscriptions/{id}/history` | История |
| GET/POST | `/visits/` | Визиты |
| POST | `/visits/entry\|exit\|check-in\|check-out\|manual\|auto-close` | Операции |
| GET | `/visits/stats/today\|week\|month` | Статистика |
| GET | `/visits/active` | В зале |

### 7.3. Доступ / СКУД / Face ID (30)

| Метод | Путь | Описание |
|---|---|---|
| POST | `/access/check\|grant\|open\|exit\|override` | Проверка доступа |
| POST | `/access/manual-open\|emergency-unlock` | Ручное открытие |
| GET | `/access/logs` | Журнал |
| POST | `/credentials/qr\|rfid\|card\|bracelet\|mobile-key\|online-lock` | Создание ключей |
| GET | `/credentials/qr/client/{id}` | QR клиента |
| POST | `/credentials/{id}/block\|unblock` | Блокировка |
| POST | `/credentials/emulate\|program\|validate\|force-write\|reassign` | Программирование |
| POST | `/dynamic-qr/generate\|validate\|my\|revoke\|verify\|guest\|group\|turnstile` | Динамические QR |
| POST | `/face-id/register\|verify\|turnstile` | Face ID |
| GET | `/face-id/engine/info\|templates` | Движок |
| POST | `/face-id/anti-spoofing\|liveness` | Защита |
| GET/POST | `/lockers/` | Шкафчики |
| POST | `/lockers/{id}/assign\|open\|block\|release` | Операции |
| POST | `/skud/checkaccess\|event\|health_check` | ITC СКУД (Basic Auth) |
| POST | `/skud/olock_checkaccess\|aqua_checkaccess\|solar/checkaccess` | СКУД доп. |
| POST | `/kerong/auth\|sync` | Kerong замки |
| POST | `/kerong/locks/register` | Регистрация замка |
| POST | `/reader/*` | RFID-ридер (PC/SC) |
| POST | `/rfid_reader/*` | RFID-операции |

### 7.4. Платежи / Касса / Онлайн (40)

| Метод | Путь | Описание |
|---|---|---|
| GET/POST | `/payments/` | Платежи |
| POST | `/payments/{id}/complete\|refund` | Завершение/возврат |
| GET | `/wallet/me\|me/balance\|me/transactions` | Кошелёк |
| POST | `/wallet/client/{id}/deposit` | Пополнение |
| POST | `/fiscal/open-shift\|close-shift\|cash-withdrawal\|x-report\|z-report` | Касса |
| POST | `/fiscal/atol\|shtrih\|refund\|correction` | Фискализация |
| GET/POST | `/fiscal/settings\|shift\|status\|ofd-check` | Настройки ККТ |
| GET/POST | `/receipts/` | Чеки |
| GET | `/receipts/{id}/pdf` | PDF чека |
| POST | `/receipts/{id}/send\|fiscalize\|print` | Отправка |
| GET/POST | `/cash-desk/open\|close\|current` | Legacy смены |
| POST | `/sales/subscription\|service` | Продажи |
| POST | `/yookassa/payments\|webhook\|refunds\|cards\|auto-charge\|test\|simulate` | ЮKassa |
| POST | `/recurring/schedules\|run\|test` | Рекурренты |
| POST | `/bank_online/*` | Онлайн-эквайринг |

### 7.5. Бухгалтерия / Отчёты / Экспорт (25)

| Метод | Путь | Описание |
|---|---|---|
| GET/POST | `/accounting/entries` | Проводки |
| GET | `/accounting/balance-sheet\|cash-flow\|osv/{period}` | Отчёты |
| POST | `/accounting/pko\|rko\|sale\|purchase\|manual-entry` | Операции |
| GET | `/accounting/export/1c\|export/buh` | Экспорт |
| GET | `/reporting/payroll\|6ndfl\|rsv\|usn-declaration\|calendar\|summary` | Реготчётность |
| GET | `/reports/operational\|hourly\|shifts` | Операционные |
| POST | `/exports/jobs\|quick` | Асинхронные выгрузки |
| GET | `/export/download?token=` | JWT-ссылка 24ч |
| POST | `/export/forget` | Анонимизация (152-ФЗ) |
| POST | `/aa/import-csv\|export\|webhook` | Интеграция A&A |
| GET | `/aa/sync-log` | Журнал A&A |

### 7.6. Аналитика / AI (12)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/analytics/dashboard\|forecast\|recalc\|heatmap` | Дашборд |
| GET | `/analytics/ai/churn\|risk-segments` | AI-отток |
| POST | `/ai/churn/train\|predict\|resolve` | Обучение |
| GET | `/ai/status` | Статус модели |
| GET | `/analytics/dashboard-chart` | HTML Chart.js |
| POST | `/self-learn/pricing/analyze\|apply` | Цены |
| POST | `/self-learn/self-heal` | Самоисцеление |
| GET | `/ml/predict/churn\|features/client` | ML |

### 7.7. Коммуникации (25)

| Метод | Путь | Описание |
|---|---|---|
| GET/POST | `/messenger/chats\|messages\|bindings\|notify\|broadcast\|notifications\|reminders\|settings` | Messenger |
| POST | `/max-bot/webhook\|link\|settings` | MAX webhook |
| POST | `/max-bot/fsm/message` | FSM |
| POST | `/telegram/webhook` | Telegram |
| WS | `/chat/ws` | WebSocket чат |
| POST | `/notify/settings\|test\|digest` | Уведомления |
| GET/POST | `/phone-verify/send\|verify\|resend` | Телефон |
| POST | `/marketing/segments\|sms\|email\|campaigns\|launch\|analytics\|roi\|ab-test` | Маркетинг |
| POST | `/miniapp/wallet\|topup\|booking` | Мини-приложение MAX |
| POST | `/max-bridge/auth\|register` | MAX Bridge |

### 7.8. Документы / Коммерция / Видео (20)

| Метод | Путь | Описание |
|---|---|---|
| GET/POST | `/documents/` | CRUD |
| POST | `/documents/{id}/sign\|sign-ep\|send-email\|print` | Подпись/печать |
| GET | `/documents/{id}/download?format=pdf\|docx` | Скачать |
| POST | `/documents/mass-generate` | Массовая генерация |
| GET | `/documents/{id}/events\|signatures\|relations\|history` | Связи |
| GET/POST | `/document_templates/` | Шаблоны |
| GET/POST | `/commercial/plans\|subscribe\|features` | Тарифы клуба |
| GET/PATCH | `/commercial/subscriptions/{club}/upgrade` | Апгрейд |
| GET/POST | `/brand/settings\|tenants\|summary` | White-label |
| GET/POST | `/branding/*` | Брендинг |
| GET/POST | `/video-ai/triggers\|events\|cameras` | Видеоаналитика |
| POST | `/video-ai/events/{id}/confirm\|false-alarm` | Feedback-loop |
| GET/POST | `/video-alerts/` | Алерты камер |
| POST | `/video-alerts/{id}/face-match` | Сопоставление |

### 7.9. Система / Setup / Ops (20)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/setup/status\|wizard` | Мастер установки |
| POST | `/setup/license/activate\|database/init\|admin/create\|club\|devices\|tariffs\|complete\|reset` | Шаги |
| GET/POST | `/setup/settings` | Настройки |
| POST | `/setup/test-connection` | Тест |
| GET/POST | `/license/status\|activate\|limits\|check` | Лицензия |
| POST | `/ops/backup/run\|restore` | Бэкапы |
| GET | `/ops/health\|replication` | Health |
| GET/POST/DELETE | `/ui-config/screens\|roles/{role}/screens\|my` | Экраны |
| GET/POST | `/feature-flags/*` | Feature flags |
| POST | `/feature-flags/rollout\|evaluate\|license-bind\|stats\|stream` | Advanced |
| GET/POST | `/club-params/*` | Параметры клуба |
| GET | `/health/` | Health БД |
| GET | `/metrics` | Prometheus |
| GET | `/sse/live/{club}` | SSE |
| WS | `/ws/alerts` | WebSocket alerts |
| POST | `/print/*` | Очередь печати |
| POST | `/dal/drivers/{pkg}/install\|discover` | DAL |
| GET/POST | `/dal/devices` | Устройства DAL |
| POST | `/dal/devices/{id}/command\|ping` | Команды |

### 7.10. Музыка / DJ (17)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/music/zones/` | Список зон |
| POST | `/music/zones/` | Создать |
| PATCH/DELETE | `/music/zones/{id}` | Изменить/удалить |
| GET | `/music/zones/{id}/status` | Статус зоны |
| POST | `/music/zones/{id}/play` | Воспроизвести |
| POST | `/music/zones/{id}/pause` | Пауза |
| POST | `/music/zones/{id}/energize` | Energize |
| POST | `/music/zones/{id}/dj` | Установить DJ-состояние |
| POST | `/music/zones/{id}/pad-fire` | Сыграть пад |
| GET | `/music/playlists/` | Список плейлистов |
| POST | `/music/playlists/` | Создать плейлист |
| GET/POST | `/music/sfx/` | Сэмплы падов |
| GET | `/music/license` | Лицензия |
| GET | `/music/agent/state?token=` | Состояние для агента |
| POST | `/music/agent/register` | Авто-регистрация |
| GET | `/music/agent/pads?token=` | Очередь падов |
| POST | `/music/agent/pads/ack` | Подтверждение |

### 7.11. Специализированные модули (дополнительно)

| Модуль | Путь | Описание |
|---|---|---|
| **Геймификация** | `/gamification/levels\|achievements\|leaderboard` | XP, уровни, награды |
| **Рефералка** | `/referrals/codes\|register\|reward\|payout\|stats` | Партнёрская программа |
| **Корпоратив** | `/corporate/companies\|contracts\|members\|invoices` | Корпоративные продажи |
| **Сезонные** | `/seasonal/campaigns\|validate\|auto-activate` | Промо-кампании |
| **Нишевые** | `/niche/templates\|apply\|clone` | Шаблоны для ниш |
| **Онлайн-запись** | `/booking-widget/public/*\|embed/{club}` | Публичный виджет |
| **Онлайн-тренировки** | `/online-training/*\|online-sessions/*` | Zoom/Meet, записи |
| **Тренеры** | `/trainers/profiles\|schedules\|bookings\|attendance\|sales\|kpi` | KPI, зарплата |
| **Услуги** | `/services/book\|availability\|trainer-schedule` | Запись на услуги |
| **Склад** | `/warehouse/products\|shop/*` | Товары, продажи |
| **Self-service** | `/selfservice/profile\|subscriptions\|visits` | Терминал |
| **Self-learning** | `/self-learn/pricing\|self-heal\|churn` | Самообучение |
| **Коннекторы** | `/connectors\|integrations-config` | 1С, CRM «ХИТ» |
| **Маркетинг** | `/marketing/campaigns\|analytics\|roi\|ab-test` | Кампании |
| **Автоматизация** | `/auto/run-daily\|stats` | Кнопка автоматики |
| **Коммерция** | `/commercial/plans\|subscribe\|features` | Тарифы клуба |

### 7.12. Коды ошибок

| Код | Значение | Когда |
|---|---|---|
| 200/201 | Успех | — |
| 400 | Бизнес-ошибка | Смена закрыта, лимит визитов, неверный формат |
| 401 | Токен/подпись | Истёк JWT |
| 403 | Право/роль | Нет права, участник чата, время тарифа, Face ID |
| 404 | Не найдено | — |
| 405 | Метод не разрешён | — |
| 409 | Конфликт | Дубль, занят слот/шкафчик, уже в клубе |
| 410 | QR использован | Истёк TTL |
| 413 | Файл >10 МБ | — |
| 422 | Валидация | Pydantic |
| 423 | Аккаунт заблокирован | 5 неверных паролей |
| 429 | Rate limit | API 10 r/s, auth 5/мин, боты 30/сек |
| 502 | ККТ/внешний API | — |
| 503 | Устройство недоступно | — |

### 7.13. Примеры запросов

**Пример 1: платёж с чеком**

```bash
B=http://localhost:8001/api/v1
tok=$(curl -s -X POST $B/auth/login -H 'Content-Type: application/json' \
     -d '{"login":"superadmin","password":"***"}' | jq -r .access_token)

# Открыть смену
curl -s -X POST $B/fiscal/open-shift -H "Authorization: Bearer $tok"

# Создать платёж
pid=$(curl -s -X POST $B/payments/ -H "Authorization: Bearer $tok" \
     -H 'Content-Type: application/json' \
     -d '{"client_id":"…","amount":300,"payment_method":"CASH","payment_direction":"INCOMING"}' \
     | jq -r .id)

# Подтвердить (чек пробивается здесь)
curl -s -X POST $B/payments/$pid/complete -H "Authorization: Bearer $tok"

# Проверить смену и проводки
curl -s $B/fiscal/shift -H "Authorization: Bearer $tok"
curl -s $B/accounting/entries -H "Authorization: Bearer $tok"
```

**Пример 2: СКУД checkaccess (ITC)**

```bash
curl -u itc:itc_secret_2026 -X POST http://IP:8001/api/v1/skud/checkaccess \
  -H "Content-Type: application/json" \
  -d '{"device_id":"192.168.1.100","client_card":"1D870731000001","request_id":"t1","direction":"entry"}'
# → {"grant_access": 1, "text_full": "Доступ разрешен."}
```

**Пример 3: Авто-регистрация агента музыки**

```bash
curl -X POST http://IP:8001/api/v1/music/agent/register \
  -H "Content-Type: application/json" \
  -d '{"machine_id":"AndreyHome-5404a625f6a6","name":"Зал AndreyHome","lib":"G:\\music"}'
# → {"zone_id":"...","agent_token":"...","registered":true}
```

**Пример 4: Feature flags evaluate**

```bash
curl -X POST http://IP:8001/api/v1/feature-flags/evaluate/new_ui \
  -H "Authorization: Bearer $tok" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user-123"}'
# → {"enabled": true, "reason": "percentage"}
```


> ⚠️ **Точное число эндпоинтов** уточняется командой:
> ```bash
> curl -s http://localhost:8001/openapi.json | jq '.paths | length'
> ```
> В v1.6.1 добавлены модули: `music/` (17), `miniapp` (5), `skud/kerong` (8) — итого больше 191.
---

## 8. RBAC: РОЛИ, ПРАВА, ЭКРАНЫ

### 8.1. Роли (9 в модели)

> ⚠️ **В источниках два разных списка ролей:**
> - **Из PDF v1.1:** superadmin, admin, manager, trainer, cashier, **receptionist**, accountant, client, **guest**
> - **Из RBAC.md:** superadmin, admin, **owner**, manager, cashier, accountant, trainer, client, **device**
>
> Ниже — **из RBAC.md** (более новая версия). Реальная матрица — в БД:
> ```sql
> SELECT code, name, is_system FROM roles ORDER BY code;
> ```

| Роль | Код | Назначение | Кол-во прав (RBAC.md) |
|---|---|---|---|
| Суперадминистратор | `superadmin` | Аварийный доступ, bypass (флаг is_superuser) | Все |
| Администратор | `admin` | Полное операционное управление клубом | 71 |
| Владелец | `owner` | Контроль без операционки | 2 |
| Менеджер | `manager` | Продажи, клиенты, тарифы | 13+ |
| Кассир / Ресепшен | `cashier` | Касса, входы | 6+ |
| Бухгалтер | `accountant` | Учёт, инкассация | 0 (набор выдать!) |
| Тренер | `trainer` | Read-only расписание | 3 |
| Клиент | `client` | Личный кабинет | 0 (заготовка) |
| Устройство | `device` | СКУД API | 0 (минимум) |

**Различия источников (PDF v1.1 vs RBAC.md):**

| Роль | Код | Назначение | В PDF v1.1 |
|---|---|---|---|
| Владелец | `owner` | Контроль без операционки | ❌ нет |
| Ресепшен | `receptionist` | Ресепшен | ✅ есть |
| Гость | `guest` | Гость | ✅ есть |
| Устройство | `device` | СКУД API | ❌ нет |

### 8.2. Формат прав

`объект.действие` — `payments.refund`, `users.delete`, `access.override`, `roles.manage`.

### 8.3. Детализация прав по ролям

**`admin` (71 право):**

- **Доступ и пользователи:** `system.admin`, `access.override`, `access.cache.manage`, `roles.manage`, `roles.read`, `permissions.read`, `users.create/read/update/delete`, `audit.read`
- **Клиенты и продажи:** `clients.create/read/update`, `subscriptions.create/read/update/cancel/freeze/renew/history`, `tariffs.create/read/update`, `services.create/read/update/delete`, `sales.create/read`, `wallet.deposit/read`, `documents.create/read/delete`
- **Касса и деньги:** `payments.create/read/update/refund`, `cash_desk.open/close/read/manage`, `receipts.read/send`, `lockers.read/update/assign/manage`
- **Клуб:** `credentials.create/read/update/delete`, `visits.create/read/update`, `face.read/manage`, `devices.create/read/update/delete`
- **Настройки:** `club_settings.read/update`, `settings.read/update`, `setup.read/write`, `ui-config.read/update`

**`owner` (2):** `audit.read`, `users.delete`

**`manager` (13+):** `clients.create/read/update`, `subscriptions.create/read/update`, `tariffs.create/read/update`, `users.delete`, `payments.create/read/update`

**`cashier` (6+):** `clients.create/read`, `subscriptions.create/read/update`, `tariffs.read`

**`accountant` (0 — нужно выдать):** рекомендуется `payments.read`, `cash_desk.read`, `receipts.read`, `audit.read`, `lockers.read`, `subscriptions.read`, `clients.read`

**`trainer` (3):** `clients.read`, `subscriptions.read`, `tariffs.read`

**`support` (2):** `clients.read`, `subscriptions.read`

### 8.4. Критичные права (guard)

- Нельзя снять `system.admin`, `roles.manage`, `users.delete` у admin.
- Нельзя удалить последнюю роль с `system.admin`.
- Нельзя выдать критичные права роли `device`.
- Нельзя скрыть `ui_config` у superadmin (защита от самоблокировки).

### 8.5. Экраны ролей (ui_config)

**Строгая модель:** не отмеченный экран — не виден вообще. Список из 17 вкладок sidebar:

| Экран | superadmin | admin | manager | cashier | trainer | reception | accountant |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| dashboard | ✅ | ✅ | ✅ | ❌ | ⚠️ | ❌ | ✅ |
| music | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| clients | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| visits | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| subscriptions | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| services | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| schedule | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| accounting | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ✅ |
| messenger | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| notifications | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| ai_center | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| users | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| audit | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| face_id | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| settings | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| credentials | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| connections | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Легенда:** ✅ — видит; ❌ — не видит; ⚠️ — ограниченно.

### 8.6. Как это работает

1. Desktop → запрос с JWT.
2. `get_current_user` → пользователь.
3. `require_permission("payments.create")` → объединение прав всех ролей.
4. Нет права → 403.
5. Действие → `audit_logs`.

### 8.7. Настройка через UI

- `Настройки → Роли и права` → роль → галочки прав → `Сохранить`. Применяется мгновенно.
- `Настройки → Экраны ролей` (superadmin) → матрица видимости экранов роли.
- **Строгая модель: пустая строка = ни одного экрана.**

### 8.8. Аудит

Все действия пишутся в `audit_logs`:
- `user_id` — кто
- `action` — что (create/update/delete/read)
- `entity_type` — над чем
- `entity_id` — ID объекта
- `before_data` / `after_data` — состояние до/после

**Retention:** настраивается через `Настройки → История → Срок хранения` (30/180/365/730 дней / бессрочно).

# ЧАСТЬ 4. ОБОРУДОВАНИЕ И СЕРВИСЫ

## 9. HARDWARE ABSTRACTION LAYER (HAL)

### 9.1. Архитектура: Strategy + Registry

```
┌──────────────────────────────────────────────────┐
│              DeviceManager (singleton)            │
├──────────────────────────────────────────────────┤
│              DriverRegistry (автообнаружение)     │
├──────────┬──────────┬──────────┬──────────┬──────┤
│EraDriver │X1Driver  │Kerong    │Generic   │Generic│
│ЭРА       │X1        │KR-*      │Modbus    │HTTP/  │
│TCP бинар │HTTP+WS   │Modbus    │TCP/RTU   │MQTT   │
└──────────┴──────────┴──────────┴──────────┴──────┘

RFID: AcsAcr1252u (PC/SC)
```

**Компоненты:**

| Файл | Назначение |
|---|---|
| `app/hardware/base.py` | `BaseDeviceDriver` — базовый класс |
| `app/hardware/manager.py` | `DeviceManager` — синглтон-менеджер |
| `app/hardware/registry.py` | `DriverRegistry` — реестр драйверов |
| `app/hardware/rfid_reader.py` | PC/SC-ридер (RFID) |
| `app/hardware/drivers/*.py` | Конкретные драйверы |

### 9.2. Поддерживаемые устройства

> ⚠️ **В PDF v1.1 указано «6 драйверов» (ЭРА, X1, Kerong + Generic).**
> Реально в `app/hardware/drivers/` — 7 файлов: `era.py`, `x1.py`, `kerong.py`,
> `generic_http.py`, `generic_modbus.py`, `generic_mqtt.py`, `acs_acr1252u.py`.
> `AcsAcr1252u` — RFID-ридер (PC/SC), не СКУД, поэтому в PDF его не считали.

| Драйвер | Вендор | Модели | Протоколы |
|---|---|---|---|
| EraDriver | ЭРА | T-1000, T-2000, C-100, C-200, C-PRO, T-UNI | TCP, HTTP API |
| X1Driver | X1 | X1-LITE, X1-PRO, X1-MAX, X1-NET, X1-WIFI | HTTP API, WebSocket |
| KerongDriver | Kerong | KR-S50, KR-S100, KR-S200, KR-M16, KR-M24, KR-M40, KR-PRO | RS-485, Modbus RTU, TCP |
| GenericModbusDriver | Generic | MODBUS-TCP, MODBUS-RTU | Modbus TCP/RTU |
| GenericHttpDriver | Generic | HTTP-API | HTTP REST |
| GenericMqttDriver | Generic | MQTT | MQTT |
| AcsAcr1252u | ACS | ACR1252U | PC/SC (RFID) |

### 9.3. Интерфейс BaseDeviceDriver

| Метод | Назначение |
|---|---|
| `connect()` | Подключиться |
| `disconnect()` | Отключиться |
| `ping()` | Проверка связи |
| `open(credential, **kwargs)` | Открыть проход |
| `close(**kwargs)` | Закрыть/блокировать |
| `release_locker(locker_id)` | Открыть шкафчик |
| `get_locker_status(locker_id)` | Статус шкафчика |
| `get_device_info()` | Информация |
| `sync_credentials(credentials)` | Синхронизация ключей |
| `start_event_listener()` | Прослушка событий |

### 9.4. Подключение нового устройства

**Способ 1: YAML-конфиг** (`config/devices.yaml`) — без кода:

```yaml
- device_id: "my_turnstile_01"
  name: "Турникет — Новый"
  vendor: "Generic"
  model: "HTTP-API"
  device_type: "turnstile"
  protocol: "http_api"
  host: "192.168.1.200"
  port: 80
  endpoints:
    open:  {method: "POST", path: "/api/open"}
    close: {method: "POST", path: "/api/close"}
    status:{method: "GET",  path: "/api/status"}
```

**Способ 2: Новый драйвер** (`app/hardware/drivers/my_device.py`):

```python
from app.hardware.base import BaseDeviceDriver, register_driver, AccessResult

@register_driver
class MyDeviceDriver(BaseDeviceDriver):
    VENDOR = "MyCompany"
    MODELS = ["MODEL-A"]

    async def connect(self) -> bool: ...
    async def open(self, credential=None, **kwargs) -> AccessResult: ...
    async def close(self, **kwargs) -> bool: ...
```

### 9.5. DAL (Device Abstraction Layer) — подсистема пакетов

Помимо HAL, есть DAL — репозиторий `.fnp`-пакетов драйверов:

| Пакет | Устройство |
|---|---|
| `atol-kkt` | АТОЛ ККТ |
| `shtrih-kkt` | Штрих-М |
| `mercury-scale` | Весы Mercury |
| `hikvision-face` | Hikvision Face ID |
| `zebra-scanner` | Сканер Zebra |

**API DAL:**

| Метод | Путь | Описание |
|---|---|---|
| POST | `/dal/drivers/{pkg}/install` | Установить драйвер |
| POST | `/dal/drivers/{pkg}/discover` | Автообнаружение |
| POST | `/dal/drivers/{pkg}/enable\|disable` | Вкл/выкл |
| POST | `/dal/drivers/{pkg}/upgrade` | Обновить |
| DELETE | `/dal/drivers/{pkg}` | Удалить |
| GET | `/dal/devices` | Список устройств |
| POST | `/dal/devices/{id}/command\|ping` | Команды |

### 9.6. СКУД ITC (внешний контроллер)

**Настройка:** через реестр Windows `HKLM\SOFTWARE\ITCService`:

```
CheckAccessURL = http://IP:8001/api/v1/skud/checkaccess
EventURL       = http://IP:8001/api/v1/skud/event
HealthCheckURL = http://IP:8001/api/v1/skud/health_check
OlockCheckAccessURL = http://IP:8001/api/v1/skud/olock_checkaccess
AquaCheckAccessURL  = http://IP:8001/api/v1/skud/aqua_checkaccess
SolarCheckAccessURL = http://IP:8001/api/v1/skud/solar/checkaccess
BasicAuthUser = itc
BasicAuthPass = itc_secret_2026
TimeoutMs     = 5000
RetryCount    = 3
```

**Схема работы:**

```
Терминал СКУД  ──checkaccess──→  FitIntel Pro
               ←──grant_access──
               ──event────────→  (запись визита)
```

### 9.7. Kerong замки (offline + online)

**Модели:** KR-S50, KR-S80, KR-S100, KR-S200, KR-M16, KR-M24, KR-M40, KR-PRO.

**Режимы:**
- **Hybrid** (рекомендуется): sync раз в 5 мин + online-проверка.
- **Offline**: whitelist до 10 000 карт локально.
- **Online**: каждое открытие — запрос к серверу.

**API:**
- `POST /kerong/auth` — проверка карты
- `POST /kerong/sync` — whitelist
- `POST /kerong/locks/register` — регистрация замка

---

## 10. КЛЮЧЕВЫЕ СЕРВИСЫ

### 10.1. Список сервисов (~55)

| Сервис | Функционал |
|---|---|
| `access_cache_service` | Кэш прав доступа (Redis) |
| `access_service` | Проверка доступа, override |
| `analytics_service` | Дашборд, KPI, отчёты |
| `audit_service` | Аудит действий |
| `auth_service` | JWT, OAuth2, токены |
| `booking_sweep` | Свип записей (напоминания, авто-отмена) |
| `bot_keyboards` | Клавиатуры для ботов |
| `bot_scenarios` | FSM-сценарии MAX-бота |
| `cash_desk_service` | Кассовые смены, сверка |
| `chat_service` | WebSocket чаты |
| `client_history_service` | История клиента (timeline) |
| `client_service` | CRUD клиентов, аудит |
| `commercial_service` | Тарифы клуба, тенанты |
| `credential_service` | QR/RFID генерация и валидация |
| `device_protocols` | Эмуляторы протоколов (Modbus/HTTP/MQTT) |
| `device_service` | CRUD устройств, heartbeat |
| `document_service` | PDF (ReportLab), подпись |
| `email_queue_service` | Очередь писем, ретраи 1→5→15 мин |
| `email_service` | SMTP-отправка |
| `entry_policy` | Единая политика входа (абонемент + бронь) |
| `export_service` | Выгрузки (xlsx/csv/json) |
| `face_id_service` | Регистрация/верификация лиц |
| `fiscal_service` | Универсальная фискализация (АТОЛ/Штрих) |
| `gamification_service` | XP, уровни, достижения, leaderboard |
| `integration_service` | Внешние системы (1С, CRM «ХИТ») |
| `license_service` | Лицензия (Ed25519) |
| `locker_service` | Управление шкафчиками |
| `marketing_service` | SMS (SMSC.ru), Email, кампании |
| `notification_service` | Email/SMS/WebPush/MAX |
| `offline_sync_service` | Офлайн-синхронизация |
| `online_training_service` | Онлайн-тренировки |
| `payment_service` | Оплата, возвраты, онлайн, webhooks |
| `print_service` | Очередь печати |
| `qr_service` | QR-генерация (HMAC-SHA256) |
| `rbac_guard` | Защита прав (guard) |
| `rbac_service` | Роли, права, матрица |
| `receipt_service` | Чеки, 54-ФЗ |
| `report_service` | Отчёты |
| `role_permission_service` | Связи ролей и прав |
| `role_service` | CRUD ролей |
| `sale_service` | Продажи абонементов, услуг |
| `sbp_service` | СБП (mock) |
| `scheduler_service` | Планировщик (APScheduler) |
| `shop_service` | Магазин (серверный/киоск) |
| `subscription_lifecycle_service` | Freeze, renew, cancel |
| `subscription_service` | Абонементы |
| `tariff_service` | Тарифы |
| `telegram_bot_service` | Telegram-бот |
| `terminal_emulator` | Терминал самообслуживания |
| `trainer_service` | Тренеры, KPI |
| `user_role_service` | Связи пользователей и ролей |
| `user_service` | CRUD пользователей |
| `visit_service` | Entry/Exit, статистика |
| `wallet_service` | Кошелёк, транзакции |
| `yookassa_service` | ЮKassa API + webhook |

### 10.2. Подпакеты

**`app/services/accounting/`:**
- `internal_accounting.py` — внутренняя SQLite-учётка (ПКО/РКО/ОСВ/P&L/баланс)
- `onec_integration.py` — интеграция с 1С (CommerceML)

**`app/services/bank/`:**
- `universal_bank.py` — адаптеры Сбер/Тинькофф/Райффайзен

**`app/services/connectors/`:**
- `base.py` — базовый коннектор
- `fitness1c.py` — 1С:Фитнес клуб (API V3)
- `sync_engine.py` — движок синхронизации

**`app/services/fiscal/`:**
- `universal_fiscal.py` — АТОЛ ДТО 10, Штрих-М, Эвотор, Меркурий

### 10.3. Ключевые потоки

**Платёж (E33):**
```
POST /payments/ (PENDING)
  → POST /payments/{id}/complete
  → сначала чек: _fiscalize (guard смены → ДТО 10 sell)
  → COMPLETED + completed_at
  → автопроводка accounting_entries (Дт 50/57 Кт 90.1)
  → баланс смены
```

**Вход клиента:**
```
идентификатор (client_id → RFID → FaceID → QR)
  → credential ACTIVE и не просрочен
  → активный абонемент (статус/лимит/временное окно)
  → списание визита
  → visit ACTIVE
Выход: длительность, авто-освобождение шкафчика
```

**Онлайн-оплата ЮKassa:**
```
create → redirect → webhook (HMAC, идемпотентность по event_key)
  → succeeded: платёж + фискальный номер + пополнение кошелька
  → активация абонемента из metadata
```

**Синхронизация 1С:**
```
коннектор fitness1c (HTTP API V3: /clients /subscriptions /visits /schedule)
  → нормализация
  → sync_engine с дедупликацией
  → журнал connector_sync_log
```

### 10.4. Фоновые задачи (Celery + APScheduler)

**Celery (`app/tasks/`):**

| Задача | Что делает |
|---|---|
| `access_control.py` | Инвалидация кэша доступа |
| `analytics.py` | Пересчёт агрегатов |
| `cleanup.py` | Очистка старых данных |
| `finance.py` | Автопроводки, сверка |
| `ml.py` | Обучение моделей |
| `notifications.py` | Email/SMS |
| `notifications_max.py` | MAX-рассылки |
| `sync_lockers.py` | Синхронизация шкафчиков |
| `sync_one_c.py` | Синхронизация 1С |
| `sync_skud.py` | Синхронизация СКУД |
| `visits.py` | Авто-закрытие визитов |

**APScheduler (в процессе API):**
- Ежедневно 00:05 — пересчёт агрегатов за вчера + прогнозы на 7 дней.
- Поток-планировщик — дайджест уведомлений в `digest_time`.

**Кэш доступа:**
- TTL 24 ч, версионирование по device_id
- Инвалидация при изменении прав
- `refresh_all_caches()` / `cleanup_expired_cache()`

---

## 11. МУЗЫКАЛЬНЫЙ МОДУЛЬ (DJ-АГЕНТ)

### 11.1. Архитектура

```
Desktop GUI (music_tab.py)
    ↓ HTTP
API (app/api/v1/music/*)
    ↓ HTTP
DJ-агент (scripts/music/agent.py)
    ↓ IPC (named pipe)
3 × mpv-процесса: Deck A, Deck B, PAD
```

### 11.2. Компоненты агента (`scripts/music/`)

| Файл | Назначение |
|---|---|
| `agent.py` | Основной цикл (fetch state, handle_dj, auto_mix, switch_to) |
| `deck.py` | Один mpv-процесс (IPC, fade, EQ, EOF) |
| `pads.py` | Очередь сэмплов, дедуп по (name, path) |
| `duck.py` | VoiceDucker — авто-дакинг музыки при речи в микрофон |
| `skud_trigger.py` | СКУД-триггер для energize (при потоке входов) |
| `fitintel_player_agent.py` | Обёртка с argparse (точка входа) |

### 11.3. Компоненты API (`app/api/v1/music/`)

| Файл | Назначение |
|---|---|
| `__init__.py` | Регистрация роутеров |
| `agent.py` | `/music/agent/state`, `/register`, `/pads`, `/pads/ack` |
| `deps.py` | Общие зависимости (ensure, row, cfg) |
| `dj.py` | `POST /zones/{id}/dj` — установка DJ-состояния |
| `zones.py` | CRUD зон |
| `playlists.py` | CRUD плейлистов |
| `schedule.py` | Расписание фоновой музыки |
| `sfx.py` | CRUD сэмплов (пады) |
| `license.py` | Лицензия фоновой музыки |

### 11.4. Ключевые фичи

- **Авто-регистрация агента** по `machine_id` (hostname + MAC).
- **Сохранение токена** в `client_settings.json`.
- **Crossfade** между деками A/B (0–30 сек).
- **Авто-микс** папки по кругу + плейлиста.
- **EQ** через lavfi (mpv v0.41: `af set equalizer=…`).
- **Пады** (1–8) — one-shot поверх музыки.
- **Дакинг** микрофона (авто-приглушение на 20%).
- **taskkill /T** при выключении — убивает всё дерево процессов.
- **Дедуп падов** — 2 сек TTL по (name, path).

### 11.5. Модели данных музыки

| Таблица | Поля |
|---|---|
| `music_zones` | id, name, provider_type, agent_token, machine_id, desired_state, desired_playlist_id, dj_state (JSON) |
| `music_playlists` | id, name, description, tracks (JSON), is_energize |
| `music_sfx` | id, name, path, volume, sort |
| `music_pad_events` | id, zone_id, sfx_id, status, created_at, acked_at |

### 11.6. Формат `dj_state` (JSON)

```json
{
  "deck_a": {"title": "Saltwater - Chicane", "path": "G:/music/Saltwater.mp3"},
  "deck_b": null,
  "active_deck": "A",
  "crossfade_seconds": 10.0,
  "master_volume": 70,
  "eq": {
    "A": {"bass": 12, "mid": 12, "treble": 12},
    "B": {"bass": 0, "mid": 12, "treble": 10}
  }
}
```

### 11.7. Функции агента

**`fetch(path)` — GET с авто-регистрацией при 403:**

```python
def fetch(self, path):
    try:
        return self._try_fetch(path)
    except urllib.error.HTTPError as e:
        if e.code != 403:
            raise
        print("AGENT | 403 Forbidden — регистрируюсь заново")
        self._register()
        return self._try_fetch(path)
```

**`handle_dj(st, dj)` — обработка DJ-состояния:**

1. Проверка `state != "playing"` → пауза.
2. Сравнение `sig` (JSON dj) с `applied_sig` — если изменилось, применить.
3. Загрузка треков через `load_paused` (если path изменился).
4. Применение EQ ко всем декам.
5. `switch_to(want_active, immediate=True)` — переключение активного.
6. Проверка остатка `rem` → авто-микс.

**`switch_to(name, cf, immediate)` — переключение деков:**

- `immediate=True`: пауза старого, play нового с мастер-громкостью.
- `immediate=False`: кроссфейд через `_fade` в отдельном потоке.
- **Фикс:** если `active == name` — resume из паузы, не дёргать.

**`auto_mix(idle_name, cf)` — авто-микс:**

1. Взять очередь папки (`folder_queue`) или плейлиста.
2. Следующий трек → `idle.load_file_paused(f)`.
3. `switch_to(idle_name, immediate=False)` — кроссфейд.

### 11.8. Регистрация и токен

**`_register()` — авто-регистрация по machine_id:**

```python
body = {"machine_id": self.machine_id,
        "name": "Зал " + socket.gethostname(),
        "lib": self.a.lib or ""}
# POST /music/agent/register → получаем новый agent_token
# Сохраняем в client_settings.json → dj_agent.token
```

**`_save_agent_token(token)` — атомарная запись в настройки:**

```python
# Читает client_settings.json
# Обновляет dj_agent.token
# Записывает через tmp-файл + os.replace
```

### 11.9. Логирование

Агент пишет в `E:\music\logs\agent_gui.log`:

```
FitIntel DJ Agent v4.5 | dry-run=False | mic=False | poll 3.0s | lib=G:\music
AGENT | machine_id=AndreyHome-5404a625f6a6
DBG | state=playing active=A master=70 mixing=False rem=200.0
DJ | resume: дек A запущен (pause=True vol=0.0 -> 70)
DJ | применено: активный дек A | мастер 70 | кроссфейд 10.0s
DJ | AUTO-MIX (папка): дек A -> B | след.: track2.mp3 | фейд 10.0s
DJ | эфир (кроссфейд): дек B | track2.mp3
PAD | Сирена | G:\music\sfx\siren.mp3
DUCK | ГОЛОС -> музыка на 14 (фактор 0.2)
DUCK | тишина -> музыка на 70
```

### 11.10. Зависимости агента

- **mpv** (v0.41+) — встроен в desktop-сборку (папка `mpv/`)
- **NSSM** (2.24-101) — для установки как службы Windows (опционально)
- **Стандартные библиотеки Python:** subprocess, threading, socket, json, os, time
- **Опционально:** `sounddevice` (для дакинга)

### 11.11. Устранение неполадок

| Симптом | Причина | Решение |
|---|---|---|
| Тишина, mpv не стартует | mpv.exe отсутствует | Проверить `_internal/mpv/mpv.exe` |
| 403 Forbidden | Устаревший токен | Авто-регистрация (машина_id) |
| `pause=true, volume=0` | switch_to не снимает паузу | Resume в switch_to |
| Не сводится | `old` не противоположный дек | Проверить switch_to |
| Пады >3 сек | `--interval 3.0` | Уменьшить до 0.5 |
| EQ FAIL | mpv без libavfilter | `mpv.com --af=help` |
| «Отключаю — играет» | taskkill без /T | taskkill /F /T |
| `lib=—` в логе | client_settings.json не рядом с exe | Скопировать в dist/ |

# ЧАСТЬ 5. ИНФРАСТРУКТУРА

## 12. ИНФРАСТРУКТУРА И РАЗВЁРТЫВАНИЕ

### 12.1. Docker Compose — обзор

| Файл | Назначение |
|---|---|
| `deploy/docker-compose.test.yml` | Тестовый профиль (сборка из исходников) |
| `deploy/docker-compose.prod.yml` | Прод (готовый образ `fitintel:prod`) |
| `deploy/docker-compose.dev.yml` | Dev-профиль |
| `deploy/monitoring/docker-compose.monitoring.yml` | Мониторинг-стек |

### 12.2. Docker Compose (test)

**Контейнеры:**
- `db` — PostgreSQL 16 (порт 5433)
- `redis` — Redis 7 (порт 6379)
- `api` — FastAPI (порт 8000 внутри)
- `nginx` — reverse proxy (порт 80 снаружи)
- `celery-worker` — фоновые задачи

**Запуск:**

```bash
cd deploy
docker compose -f docker-compose.test.yml up -d --build
```

При первой сборке компилируется dlib — 5–30 минут. **Не прерывать.**

### 12.3. Docker Compose (prod)

**Поставка через `docker load`:**

```bash
docker load -i fitintel-prod_v1.6.1.tar.gz
cd deploy
docker compose -f docker-compose.prod.yml up -d
```

**Особенности prod:**
- Секреты обязательны в `deploy/.env` (`POSTGRES_PASSWORD:?`)
- Лимиты BLAS-потоков: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` (иначе dlib/отчёты висят 10–60 с)

### 12.4. Docker Compose (dev)

```bash
cd deploy
docker compose -f docker-compose.dev.yml up -d
```

**Внимание:** в `docker-compose.dev.yml` жёстко задан пароль БД — не использовать для прода.

### 12.5. Мониторинг

```bash
cd deploy/monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

**7 контейнеров:**
- Prometheus :9090 (retention 30 дней)
- Grafana :3000 (admin/admin — **сменить!**)
- Loki :3100 (хранилище логов)
- Promtail (сбор логов всех контейнеров)
- node-exporter (системные метрики)
- cAdvisor (метрики контейнеров)
- Alertmanager :9093 (receiver «null» — **настроить!**)

**Провиженинг:** дашборды и datasources подгружаются автоматически.

### 12.6. Nginx

**Тест:** plain :80 → api:8000
**Прод:** редирект 80→443, TLS 1.2/1.3

**Rate limit:**
- API: 10 r/s (burst 20)
- `/auth/login|token`: 5 r/min (burst 5)

### 12.7. Дополнительные каталоги `deploy/`

| Каталог | Назначение |
|---|---|
| `deploy/ansible/` | Ansible-плейбуки |
| `deploy/systemd/` | Systemd-юниты (Linux) |
| `deploy/terraform/` | Terraform (Yandex Cloud) |
| `deploy/nginx/` | Reverse proxy, TLS |
| `deploy/backup/` | Скрипты бэкапа (backup.ps1 + restore.ps1) |

### 12.8. Требования к серверу

| Параметр | Минимум | Рекомендуется |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 ГБ | 8 ГБ |
| Диск | 40 ГБ SSD | 80 ГБ SSD |
| ОС | Ubuntu 20.04+/22.04 LTS | Ubuntu 22.04 LTS |
| Docker | Engine 24+ + Compose plugin | То же + fail2ban, NTP |
| Порты | 80, 22 | + 443, 9090, 3000 (только внутри) |

### 12.9. Рабочие места (desktop)

| Параметр | Значение |
|---|---|
| ОС | Windows 10/11 x64 |
| RAM | 4 ГБ |
| Диск | 500 МБ |
| Разрешение | от 1280×800 |
| Сеть | Доступ до сервера по TCP 8001 (или 80/443) |
| Периферия | Камера (Face ID), USB-считыватель RFID (PC/SC), принтер |

### 12.10. Установка сервера (Ubuntu)

```bash
# 1. Docker
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker

# 2. Клонирование
cd ~
git clone https://<ТОКЕН>@github.com/Kant84/fitintel-pro.git
cd fitintel-pro
git checkout main

# 3. Конфигурация (опционально)
nano deploy/.env
# POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, SECRET_KEY

# 4. Запуск
cd deploy
docker compose -f docker-compose.test.yml up -d --build
docker compose -f docker-compose.test.yml ps

# 5. Инициализация БД
docker compose -f docker-compose.test.yml exec api python -m scripts.bootstrap_db
docker compose -f docker-compose.test.yml exec api python -m app.db.seed.run_seed

# 6. Создание администратора
docker compose -f docker-compose.test.yml exec \
  -e SEED_ADMIN_EMAIL="admin@club.ru" \
  -e SEED_ADMIN_USERNAME="admin" \
  -e SEED_ADMIN_PASSWORD="СложныйПароль123" \
  api python -m app.db.seed.seed_admin

# 7. Проверка
curl -s http://localhost/api/v1/health/
# {"status":"ok","app":"FitIntel Pro","module":"crm","database":"ok"}
```

### 12.11. Установка desktop (Windows)

1. Получите `FitIntelDesktop-Setup_v1.6.1.exe` (~154 МБ).
2. Проверьте хеш SHA256 (см. `RELEASES.md`).
3. Запустите — администраторские права не требуются.
4. Мастер установки:
   - Приветствие → «Далее»
   - Папка установки → «Далее»
   - **Диалог «Адрес сервера клуба»** → введите `http://<IP-сервера>/api/v1` → «Далее»
   - Ярлыки → «Далее»
   - Установка (~1 минута)
   - «Завершить»

**Портабельный вариант:** `FitIntelDesktop.exe` (onefile) можно не устанавливать — положите в любую папку.

**Настройки:** `client_settings.json` рядом с exe (`api_base`, `theme`, `dj_agent`).

---

## 13. КОМАНДЫ АДМИНИСТРИРОВАНИЯ

### 13.1. Docker — базовые

```bash
# Запуск тест-профиля
cd ~/fitintel-pro/deploy
docker compose -f docker-compose.test.yml up -d --build

# Статус
docker compose -f docker-compose.test.yml ps

# Перезапуск API
docker compose -f docker-compose.test.yml restart api

# Логи (без health-спама)
docker compose -f docker-compose.test.yml logs -f api 2>&1 | grep -v health

# Логи celery
docker compose -f docker-compose.test.yml logs -f celery-worker

# Остановка
docker compose -f docker-compose.test.yml down

# ПОЛНЫЙ сброс (ВСЕ ДАННЫЕ УДАЛЯТСЯ!)
docker compose -f docker-compose.test.yml down -v

# Пересборка без кэша
docker compose -f docker-compose.test.yml build --no-cache api
docker compose -f docker-compose.test.yml up -d api
```

### 13.2. База данных

```bash
# Консоль psql
docker exec -it deploy-db-1 psql -U fitnexus_user -d fitnexus_ai

# Выполнить запрос
docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai \
  -c "SELECT id, name, desired_state FROM music_zones;"

# Список таблиц
docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c "\dt"

# Структура таблицы
docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c "\d clients"

# Размер БД
docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai \
  -c "SELECT pg_size_pretty(pg_database_size('fitnexus_ai'));"
```

### 13.3. Инициализация и seed

```bash
# Таблицы по моделям
docker compose -f docker-compose.test.yml exec api python -m scripts.bootstrap_db

# Справочники (роли, права)
docker compose -f docker-compose.test.yml exec api python -m app.db.seed.run_seed

# Создание администратора
docker compose -f docker-compose.test.yml exec \
  -e SEED_ADMIN_EMAIL="admin@club.ru" \
  -e SEED_ADMIN_USERNAME="admin" \
  -e SEED_ADMIN_PASSWORD="СложныйПароль123" \
  api python -m app.db.seed.seed_admin

# Демо-данные (услуги, тренеры, записи)
docker cp scripts/seed_demo_data.py deploy-api-1:/app/scripts/
docker exec -w /app deploy-api-1 python scripts/seed_demo_data.py
```

### 13.4. Миграции

```bash
# Применить все
docker compose -f docker-compose.test.yml exec api alembic upgrade head

# Текущая версия
docker compose -f docker-compose.test.yml exec api alembic current

# История
docker compose -f docker-compose.test.yml exec api alembic history

# Откат на N
docker compose -f docker-compose.test.yml exec api alembic downgrade -1
```

### 13.5. Проверка API

```bash
# Health
curl -s http://localhost/api/v1/health/
# {"status":"ok","app":"FitIntel Pro","module":"crm","database":"ok"}

# Расширенный health
curl -s http://localhost/api/v1/ops/health

# Swagger
open http://localhost:8001/docs

# OpenAPI JSON
curl -s http://localhost:8001/openapi.json | jq '.paths | keys[]'
```

### 13.6. Логи и диагностика

```bash
# Логи API
docker compose -f docker-compose.test.yml logs api --tail 100

# Логи конкретного контейнера
docker logs deploy-api-1 --tail 100

# Логи с grep
docker compose -f docker-compose.test.yml logs api | grep -i error

# Метрики Prometheus
curl -s http://localhost:9090/metrics

# Loki — список контейнеров
curl -s http://localhost:3100/loki/api/v1/label/container/values
```

### 13.7. Бэкапы

**Автоматический (Linux cron):**

```bash
bash ~/fitintel-pro/scripts/backup/install_cron.sh
# Создаёт backup.env + задание в cron
# Бэкап: pg_dump → gzip → ротация 14 дней
# Лог: /var/log/fitintel-backup.log
```

**Ручной (Windows PowerShell):**

```bash
$env:PGPASSWORD = "your_db_password"
pg_dump -h localhost -U fitnexus_user -d fitnexus_ai > backup_$(date +%Y%m%d).sql
```

**Восстановление:**

```bash
gunzip -c db_ДАТА.sql.gz | docker compose -f deploy/docker-compose.test.yml exec -T db \
  psql -U fitnexus_user -d fitnexus_ai
```

**Через API:**

```bash
curl -X POST http://localhost/api/v1/ops/backup/run -H "Authorization: Bearer $tok"
curl -X POST http://localhost/api/v1/ops/restore -H "Authorization: Bearer $tok" \
  -H "Content-Type: application/json" \
  -d '{"filename": "backup_20261016.sql"}'
```

### 13.8. Мониторинг

```bash
# Grafana
open http://<IP>:3000   # admin/admin (сменить!)

# Prometheus targets
open http://<IP>:9090/targets

# Loki в Grafana: Explore → {container="deploy-api-1"}
```

### 13.9. Обновление

**Тест-профиль:**

```bash
cd ~/fitintel-pro
git pull
cd deploy
docker compose -f docker-compose.test.yml build api
docker compose -f docker-compose.test.yml up -d api

# Проверка фикса
docker exec deploy-api-1 grep -c "has_track" /app/app/api/v1/music/dj.py
```

**Прод (через новый образ):**

```bash
docker load -i fitintel-prod_v1.6.2.tar.gz
cd deploy
docker compose -f docker-compose.prod.yml up -d
```

### 13.10. Сборка установщика desktop

```powershell
cd "E:\FitNexus AI\FitIntel AI\fitintel-desktop"

# 1. Сборка PyInstaller
Remove-Item dist -Recurse -Force
Remove-Item build -Recurse -Force
pyinstaller FitIntelDesktop.spec --noconfirm

# 2. Проверка содержимого
Get-ChildItem dist\FitIntelDesktop\_internal\mpv\
Get-ChildItem dist\FitIntelDesktop\_internal\tools\
Get-ChildItem dist\FitIntelDesktop\_internal\scripts\music\

# 3. Сборка установщика
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# 4. Результат
Get-ChildItem installer_out\
# FitIntelDesktop-Setup_v1.6.1.exe (~154 МБ)
```

### 13.11. Сборка mpv (в комплект)

```powershell
# Распаковать 7z-архив mpv
& "C:\Program Files\7-Zip\7z.exe" x "F:\Downloads\mpv-x86_64-*.7z" `
   -o"$env:TEMP\mpv_unpack" -y

# Скопировать в проект
Copy-Item "$env:TEMP\mpv_unpack\mpv.exe" "mpv\" -Force
Copy-Item "$env:TEMP\mpv_unpack\mpv.com" "mpv\" -Force
Copy-Item "$env:TEMP\mpv_unpack\d3dcompiler_43.dll" "mpv\" -Force
```

### 13.12. Установка NSSM (служба Windows)

```powershell
# Распаковать nssm
Expand-Archive -Path "F:\Downloads\nssm-2.24-101-g897c7ad.zip" `
   -DestinationPath "$env:TEMP\nssm_unpack" -Force

# Скопировать 64-bit версию
New-Item -ItemType Directory -Path "tools" -Force
Copy-Item "$env:TEMP\nssm_unpack\nssm-2.24-101-g897c7ad\win64\nssm.exe" `
          "tools\nssm.exe" -Force

# Проверить
& "tools\nssm.exe" version
# 2.24-101-g897c7ad 64-bit 2017-04-26
```

### 13.13. Диагностика DJ-агента

```powershell
# Лог агента
Get-Content E:\music\logs\agent_gui.log -Wait -Tail 20

# Процессы mpv
Get-Process mpv -ErrorAction SilentlyContinue | Select-Object Id, Path

# Убить всё (при зависании)
Get-Process mpv | Stop-Process -Force
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*fitintel_player_agent*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### 13.14. Проверка mpv

```powershell
# Версия (через mpv.com, не mpv.exe!)
& "C:\mpv\mpv.com" --version

# Список фильтров (проверка EQ)
& "C:\mpv\mpv.com" --af=help 2>&1 | Select-String "equalizer"

# Тест файла
& "C:\mpv\mpv.com" "G:\music\test.mp3"
```

### 13.15. Работа с БД — частые SQL

```sql
-- Список зон музыки
SELECT id, name, provider_type, desired_state, machine_id
FROM music_zones ORDER BY name;

-- Очистка мусора в музыке
DELETE FROM music_sfx WHERE name IS NULL OR path IS NULL OR path = '';

-- Дубли сэмплов
DELETE FROM music_sfx a USING music_sfx b
WHERE a.id > b.id AND a.path = b.path;

-- Список зон для агента
SELECT id, name, agent_token, machine_id, desired_state
FROM music_zones WHERE provider_type = 'local_agent';

-- Миграция legacy enum в clients
UPDATE clients SET gender='MALE'  WHERE gender IN ('МУЖСКОЙ','мужской','М','m','male');
UPDATE clients SET gender='FEMALE' WHERE gender IN ('ЖЕНСКИЙ','женский','Ж','f','female');
UPDATE clients SET client_category='ADULT' WHERE client_category IN ('ОБЫЧНАЯ','REGULAR','regular');
UPDATE clients SET status=UPPER(status) WHERE status <> UPPER(status);

-- Пользователи с ролями
SELECT u.username, u.email, r.code AS role
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.id
LEFT JOIN roles r ON r.id = ur.role_id
WHERE u.is_active = TRUE;

-- Зоны с плейлистами
SELECT z.name AS zone, p.name AS playlist
FROM music_zones z
LEFT JOIN music_playlists p ON p.id = z.desired_playlist_id;
```

### 13.16. Полезные алиасы PowerShell

```powershell
function dlog { Get-Content E:\music\logs\agent_gui.log -Wait -Tail 20 }
function mpvls { Get-Process mpv -ErrorAction SilentlyContinue | Select-Object Id, Path }
function dbq($q) { docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c $q }
function apilog { docker compose -f deploy/docker-compose.test.yml logs api --tail 100 }
```

---

## 14. БЕЗОПАСНОСТЬ

### 14.1. Аутентификация

- **JWT:** HS256, `SECRET_KEY` из `.env`.
- **Access token:** 30 мин.
- **Refresh token:** 7 дней.
- **Блокировка:** 5 неверных паролей → 5 мин (HTTP 423).
- **Superadmin:** `force_change_password` при первом входе.

### 14.2. Пароли

- **bcrypt (passlib):** 12 rounds.
- **Требования:** минимум 8 символов.
- **Хранение:** только хеши.
- **Legacy-проблема:** в dev-режиме пароль может храниться в `client_settings.json` (saved_password). В проде — убрать или шифровать (DPAPI/CredMan).

### 14.3. Секреты — где хранятся

| Где | Что |
|---|---|
| `.env` (не в git!) | SECRET_KEY, POSTGRES_PASSWORD, SMTP_PASSWORD, LICENSE_SECRET |
| БД (`fiscal_settings`) | Пароль ДТО ККТ |
| БД (`notification_settings`) | Пароль SMTP |
| БД (`integration_settings`) | Ключи интеграций (**открытым текстом — TODO: шифровать Fernet/Vault**) |
| `client_settings.json` | `dj_agent.token`, `api_base` |

**Перед продом:** сменить ВСЕ секреты, которые были в git-истории.

### 14.4. HTTPS

```nginx
server {
    listen 443 ssl;
    server_name fitintel.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location /api/v1/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 14.5. Rate limit (nginx)

| Путь | Лимит |
|---|---|
| API общий | 10 r/s (burst 20) |
| `/auth/login|token` | 5 r/min (burst 5) |
| Боты (Telegram/MAX) | 30 r/s |

### 14.6. RBAC (сокращённо)

- 9 ролей, 51 разрешение.
- `require_permission("...")` на каждом эндпоинте.
- Guard: защита критичных прав.
- Аудит всех действий.

### 14.7. 152-ФЗ (персональные данные)

- **Face ID:** только self-hosted (НЕ FindFace, НЕ NtechLab, НЕ Face++).
- **Биометрия:** особая категория ПДн → согласие клиента.
- **Фото:** хранятся в volume `face_photos` (chmod 600), только если включено.
- **Анонимизация:** `POST /clients/{id}/anonymize` — ФИО/телефон/email → `***`.
- **Право на забвение:** `POST /export/forget`.
- **Экспорт персональных данных:** `GET /export/download?token=` (JWT 24ч).

### 14.8. 54-ФЗ (фискализация)

- ДТО 10 (АТОЛ), Штрих-М Web JSON v2.
- ОФД: через API оператора.
- Проверка смены на сервере перед чеком.
- Повторная фискализация того же `receipt_id` → 400 (идемпотентность).

### 14.9. Лицензия

- **Ed25519:** ключ `FIPRO-<base64>.<sig>`.
- **Одноразовая привязка** к machine-id.
- **Soft/hard-режим:** soft — предупреждение, hard — блокировка при превышении лимита.
- **Активация:** при первом запуске (окно активации) или через экран «Лицензия».

### 14.10. Пароль ДТО ККТ

- Хранится в БД (`fiscal_settings`), не в открытом виде.
- Доступ к API-эндпоинтам `/fiscal/settings` — только admin.
- Пустой `dto_url` = эмуляция чеков (не для боя).

### 14.11. Внешние интеграции

| Что | Как защищено |
|---|---|
| ЮKassa webhook | HMAC-подпись + идемпотентность `event_key` |
| ITC СКУД | HTTP Basic Auth (ITC_BASIC_USER/PASSWORD) |
| MAX/Telegram | Bearer token в заголовке |
| SMTP | SSL/TLS + пароль приложения |
| 1С API V3 | Логин/пароль в `integration_settings` (TODO: шифровать) |

---

## 15. ИНТЕГРАЦИИ

### 15.1. Платёжные системы

| Система | Статус | Комментарий |
|---|---|---|
| ЮKassa | Готово | Webhook с HMAC, идемпотентность, автосписания |
| Сбер | Готово | sbrf.dll + REST `register.do` |
| Тинькофф | Готово | Init/Cancel/Confirm, подпись SHA-256 |
| Райффайзен | Заготовка | — |
| СБП | Mock | До сертификатов (Альфа: mTLS + RSA) |

### 15.2. ККТ

| ККТ | Статус |
|---|---|
| АТОЛ (ДТО 10) | Готово |
| Штрих-М (Web JSON v2) | Готово |
| Эвотор (Cloud) | Готово |
| Меркурий (InfoSoft) | Готово |
| Mock :18004 | Для теста |

### 15.3. Мессенджеры

| Канал | Статус | Комментарий |
|---|---|---|
| MAX (бот + FSM) | Готово | Токен из `max_bot_settings` или env |
| Telegram | Готово | Bot API |
| Email (SMTP + очередь) | Готово | Два профиля: club + system |
| SMS (smsc.ru) | Готово | — |
| Web Push (VAPID) | Готово | pywebpush |

### 15.4. Внешние системы

| Система | Статус |
|---|---|
| 1С:Фитнес клуб (API V3) | Готово |
| CommerceML 2.0 | Готово |
| CRM «ХИТ» (B-Office) | Заготовка (нужна документация) |
| A&A (CSV/webhook) | Готово |
| OData (1С) | Заготовка |

### 15.5. Оборудование

| Устройство | Протокол |
|---|---|
| Турникеты ЭРА | TCP/HTTP |
| X1 | HTTP/WS |
| Kerong замки | Modbus/RS-485 |
| RFID-ридеры | PC/SC |
| Камеры ONVIF | ONVIF |
| СКУД ITC | HTTP Basic Auth |
| ККТ АТОЛ | ДТО 10 (TCP :16732) |

### 15.6. Особенности MAX Bot

- База API: `https://platform-api.max.ru`
- Long Polling (dev): `platform-api2.max.ru` — **не использовать в проде!** (сертификат Минцифры не в стандартных хранилищах)
- Webhook (prod): HTTPS с доверенным сертификатом
- Бота может создать только верифицированное юрлицо РФ
- Rate limit: 30 запросов/сек

### 15.7. Особенности ЮKassa

- Ключи: `shop_id` + `secret_key` в `club_params` (или env)
- Режимы: `test` / `yookassa` / `sbp`
- Webhook: `https://<домен>/api/v1/yookassa/webhook`
- Секрет: `YOOKASSA_WEBHOOK_SECRET` (HMAC)
- Антидубль: `event_key` в `yookassa_webhook_events`
- Тестовые карты: 5555 5555 5555 4444 (успех), 5555 5555 5555 4477 (отказ), 3DS 12345

### 15.8. Особенности 1С:Фитнес клуб

**Настройка в 1С:**
- Роли: «Удалённый доступ внешнее приложение» + «Запуск внешнего соединения»
- Адрес API: `http://<сервер-1С>/<база>/hs/api3`

**Что синхронизируется:**
- Клиенты (поиск по телефону, без дублей)
- Абонементы (тарифы-импорты `IMP_*`)
- Визиты (дедуп по времени)

**Журнал:** `connector_sync_log`

### 15.9. Особенности ITC СКУД

- Настройка через реестр Windows (см. 9.6)
- 6 URL: checkaccess, event, health_check, olock, aqua, solar
- Basic Auth (ITC_BASIC_USER/PASSWORD из env)
- Таймаут 3–5 сек (при недоступности — локальная логика контроллера)

### 15.10. Особенности A&A

- Импорт CSV: колонки `ФИО;Телефон;Email;Дата рождения;Пол;Категория;Статус;Фото(URL)`
- Экспорт: JSON / CSV
- Webhook: `POST /aa/webhook` (входящий от A&A)
- Журнал: `/aa/sync-log`

---

## 16. МОНИТОРИНГ, ЛОГИ, БЭКАПЫ

### 16.1. Логи

| Где | Что |
|---|---|
| `docker compose logs api` | API (без health-спама) |
| `docker compose logs celery-worker` | Celery |
| `E:\music\logs\agent_gui.log` | DJ-агент |
| `fitintel-desktop/logs/client_YYYYMMDD.log` | Desktop |
| Loki :3100 | Все контейнеры (Promtail) |
| `logs/app.log` | Backend (ротация 10 МБ × 5) |
| `logs/error.log` | Только WARNING+ (10 МБ × 3) |
| `logs/access.log` | HTTP-запросы |

### 16.2. Метрики

| Endpoint | Что |
|---|---|
| `/health/` | БД |
| `/ops/health` | БД + диск + память + последний бэкап |
| `/metrics` | Prometheus |
| `/rbac/health` | RBAC |

### 16.3. Дашборды Grafana

**«FitIntel API»:**
- RPS, 5xx%, p95 латентность
- Топ-5 медленных путей
- Панель логов Loki

**«FitIntel System»:**
- CPU/RAM/диск сервера
- Таргеты up/down
- Топ-5 контейнеров по CPU/RAM

### 16.4. Алерты (Prometheus rules)

Файл `prometheus/rules/fitintel.yml`:

| Алерт | Условие | Severity |
|---|---|---|
| HighErrorRate | 5xx > 0.1/s, 2 мин | critical |
| HighLatency | p95 > 0.2с, 5 мин | warning |
| APIDown | up == 0, 1 мин | critical |
| DiskSpaceLow | < 10% | warning |
| MemoryHigh | < 10% | warning |
| PostgreSQLDown | up == 0 | critical |

**Alertmanager:** receiver «null» — **заглушка!** Настроить email/webhook.

### 16.5. Бэкапы

**Windows-хост:**

```powershell
# Ручной
$env:PGPASSWORD = "your_db_password"
pg_dump -h localhost -U fitnexus_user -d fitnexus_ai > backups\backup_$(date +%Y%m%d).sql

# Ротация 14 дней
Get-ChildItem backups\*.sql | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-14) } | Remove-Item

# Восстановление
.\scripts\backup\restore.ps1 backup_20261016.sql
```

**Linux-прод:**

```bash
# Cron install (одна команда)
bash ~/fitintel-pro/scripts/backup/install_cron.sh

# Что делает:
# - pg_dump → gzip
# - сохраняет в ./backups (volume db)
# - ротация 14 дней
# - опционально HDD/Cloud (rclone)
# - лог /var/log/fitintel-backup.log
```

**Что НЕ входит в бэкап:**
- Redis (кэш, восстанавливается)
- Файлы загрузок (чат, документы) — только если в volume
- `face_photos` (volume — отдельно)
- Только PostgreSQL

### 16.6. Ops API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/ops/backup/run` | Запустить бэкап |
| POST | `/ops/backup/restore` | Восстановить (эмуляция — не выполняет psql) |
| POST | `/ops/backup/config` | Настроить ротацию |
| GET | `/ops/health` | Расширенный health |
| GET | `/ops/replication` | Статус репликации (single-node) |

### 16.7. Диагностика почты

**Логи писем:**

```bash
docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c \
"SELECT recipient, subject, status, attempts, left(last_error,80) AS err, created_at
 FROM email_queue ORDER BY created_at DESC LIMIT 20;"
```

**Застрявшие письма:**

```bash
docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c \
"SELECT recipient, status, attempts, last_error
 FROM email_queue WHERE status <> 'SENT' ORDER BY created_at DESC;"
```

**Ручной процессинг:**

```bash
docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c \
"UPDATE email_queue SET attempts=0, next_attempt_at=NULL WHERE status='PENDING';"

docker exec -w /app deploy-api-1 python -c "
from app.db.session import SessionLocal
from app.services.email_queue_service import EmailQueueService
print(EmailQueueService(SessionLocal()).process_queue())"
# {'processed': N, 'sent': N, 'failed': 0, ...}
```

**Тест SMTP:**

```bash
docker exec -i deploy-api-1 python - <<'EOF'
from app.db.session import SessionLocal
from sqlalchemy import text
import smtplib
db = SessionLocal()
host, port, user, pwd = db.execute(text(
    "SELECT smtp_host, smtp_port, smtp_user, smtp_pass FROM notification_settings WHERE id=1")).first()
print("connect:", host, port, user)
try:
    srv = smtplib.SMTP_SSL(host, int(port or 465), timeout=15)
    srv.login(user, pwd)
    print("AUTH OK")
    srv.quit()
except Exception as e:
    print("AUTH FAIL:", str(e)[:150])
EOF
```

### 16.7а. Два профиля SMTP

FitIntel Pro поддерживает **два независимых профиля SMTP**:

| Профиль | Кто | Зачем | Где настраивается |
|---|---|---|---|
| **club** (по умолчанию) | Почта **клуба** | Рассылки клиентам, тестовые письма, дайджест | Desktop → «Уведомления → Email» (пишется в БД `notification_settings`) |
| **system** | Почта **разработчика** (`support@fixintel.ru`) | Алерты мониторинга, лицензии, поддержка клубов | env сервера: `SYSTEM_SMTP_*` |

**Принцип:** клуб не видит системный профиль и не может завалить ящик разработчика; мониторинг не зависит от настроек клуба.

**Поток письма (A4 — очередь):**
```
Отправка ВСЕГДА через таблицу email_queue
  → статусы PENDING → SENT/FAILED
  → ретраи 1 → 5 → 15 мин
  → после 3 попыток FAILED
Нет «мгновенной отправки» — письмо копится и уходит процессингом.
```

**Настройка системного профиля (env сервера):**

```ini
SYSTEM_SMTP_HOST=mail.fixintel.ru
SYSTEM_SMTP_PORT=465
SYSTEM_SMTP_USER=support@fixintel.ru
SYSTEM_SMTP_PASSWORD=<пароль ящика support>
SYSTEM_SMTP_FROM=support@fixintel.ru
```

После изменения: `docker compose -f docker-compose.test.yml up -d --force-recreate api`.

**Проверка:**
```bash
docker exec deploy-api-1 python -c "from app.core.config import settings; print(settings.SYSTEM_SMTP_HOST, settings.SYSTEM_SMTP_USER)"
```

**Отправка системного письма из кода:**
```python
NotificationService(db).send_system_email(кому, тема, текст)  # профиль system
```

**Пароль приложения — правило почтовика:**

| Почтовик | Что вписывать |
|---|---|
| mail.ru | **Пароль приложения** (Настройки аккаунта → Безопасность → Пароли приложений). Пароль ящика НЕ подойдёт — mail.ru вернёт `535 Application password is REQUIRED` |
| Yandex / Gmail | Пароль приложения (только при включённой 2FA) |
| Свой сервер (Mailcow и др.) | Обычный пароль ящика |

**Типичные ошибки:**

| Симптом (`last_error` / ответ) | Причина | Лечение |
|---|---|---|
| `535 ... Application password is REQUIRED` (mail.ru) | Вписан пароль ящика вместо пароля приложения | Создать пароль приложения |
| `535 5.7.8 authentication failed` | Неверный пароль ИЛИ хост не принадлежит почтовику ящика | Проверить пароль, хост = сервис ящика |
| Письмо висит `PENDING`, ошибок нет | SMTP не заполнен в настройках | Заполнить и сохранить, затем процессинг |
| Timeout/нет соединения | Порт закрыт файрволом, не тот порт | 465 SSL / 587 TLS; `openssl s_client -connect host:465` |

### 16.8. Статусы email_queue

| Статус | Значение |
|---|---|
| `PENDING` | Ждёт отправки (SMTP не настроен или backoff до ретрая) |
| `SENT` | Отправлено |
| `FAILED` | 3 неудачные попытки, смотреть `last_error` |

**Ретраи:** 1 → 5 → 15 мин, после 3 попыток FAILED.

**Два профиля SMTP:**
- **club** — почта клуба (из БД, `notification_settings`)
- **system** — почта разработчика (из env, `SYSTEM_SMTP_*`)

### 16.9. Мониторинг системы через Grafana

**Дашборд «FitIntel API»:**
- RPS, 5xx%, p95, топ путей
- Логи Loki

**Дашборд «FitIntel System»:**
- CPU/RAM/диск сервера
- Таргеты up
- Топ контейнеров

**Grafana по умолчанию:** admin/admin — **сменить сразу!**

### 16.10. Retention и ротация

| Что | По умолчанию | Настройка |
|---|---|---|
| Логи приложения | 10 МБ × 5 | `app/core/logging.py` |
| Логи ошибок | 10 МБ × 3 | `app/core/logging.py` |
| Бэкапы БД | 14 дней | `scripts/backup/backup.env` |
| Audit logs | 365 дней | `Настройки → История → Срок хранения` |
| Prometheus | 30 дней | `deploy/monitoring/prometheus/prometheus.yml` |
| Loki | default | `deploy/monitoring/loki/` |
| Email queue (acked) | 1 день | Автоочистка в `/music/agent/pads/ack` |
| Pad events | 1 день | То же |

# ЧАСТЬ 6. ДИАГНОСТИКА И ПРИЛОЖЕНИЯ

## 17. УСТРАНЕНИЕ НЕПОЛАДОК

### 17.1. Desktop — общие проблемы

| Симптом | Причина | Решение |
|---|---|---|
| «Сервер не подключён» (статус-бар) | API down или неверный адрес | `curl http://IP/api/v1/health/`; проверить `api_base` в «Подключениях» |
| 401 в цикле | Истёк JWT | Авто-перелогин (E70) или повторный вход |
| «Не удалось загрузить экран» | Ошибка инициализации | Запустить `python main.py` из консоли → traceback |
| Старая версия после сборки | Старый exe | Запускать `dist\FitIntelDesktop.exe` (проверить LastWriteTime) |
| Пустое меню (нет вкладок) | Строгая модель `ui_config` | «Настройки → Экраны ролей» → отметить |
| «Вечный круг» смены пароля | `is_first_login` не сброшен | `/auth/change-password` делает UPSERT `license_state` |
| 422 при входе | Клиент шлёт form-data на `/auth/token` | Проверить `api/client.py`: должен быть `POST /auth/login`, `json=` |
| `'ApiClient' object has no attribute '_e55_*'` | Старый `client.py` | Обновить client.py (E55_EXT) |
| Медленный старт (3–5 сек) | Onefile распаковывается в `%TEMP%` | Норма, либо собрать onedir |
| Ошибка «no module named 'windows.X'» | PyInstaller не подхватил модуль | Добавить в `hiddenimports` в .spec |

### 17.2. Desktop — окна и подвкладки

| Симптом | Причина | Решение |
|---|---|---|
| Окно не открывается | Ошибка в конструкторе | `python main.py` из консоли → traceback |
| F1 не работает | help_dialog.py не найден | Проверить файл в `windows/` |
| Табло с часами (F11) не показывается | clock_board.py не подхватился | Перезапуск GUI |
| RFID-плашка не появляется | Плагин rfid не активен | Проверить `rfid_monitor_widget.py` |
| Печать/PDF пустая | Нет данных или ошибка | «На этом экране нет данных для печати» |

### 17.3. Музыка / DJ

| Симптом | Причина | Решение |
|---|---|---|
| Тишина, mpv не стартует | mpv.exe отсутствует | Проверить `_internal/mpv/mpv.exe` в сборке |
| 403 Forbidden в логе агента | Устаревший `agent_token` | Агент авто-регистрируется заново (machine_id) |
| `pause=true, volume=0` — стоит на паузе | `switch_to` не снимает паузу | Проверить логику `switch_to` в agent.py |
| Не сводится (нет кроссфейда) | `old` не противоположный дек | Проверить `switch_to` |
| Пады не отвечают >3 сек | `--interval 3.0` в аргументах агента | Уменьшить до 0.5 в music_tab.py |
| EQ FAIL: invalid parameter | mpv без libavfilter | Проверить `mpv.com --af=help` |
| «Отключаю — продолжает играть» | taskkill без /T | Проверить `_stop_agent` (taskkill /F /T) |
| `lib=—` в логе | client_settings.json не рядом с exe | Скопировать в `dist/` |
| Пады дублируются (5 раз подряд) | Нет дедупа по (name, path) | Проверить `pads.py` |
| Пады SKIP not found | Файл не найден | Проверить путь в `music_sfx.path` |

### 17.4. Касса

| Симптом | Причина | Решение |
|---|---|---|
| 400 «Смена закрыта» | Чек при закрытой смене | «🔓 Открыть смену» |
| Баланс 0 после подтверждения | `completed_at < opened_at` | Новые платежи — в открытой смене |
| 502 «Касса недоступна» | `dto_url`/сеть | «⚙ Настройки кассы», ping ККТ |
| 502 «Касса вернула ошибку: N» | Mock в старом состоянии / отказ ККТ | Перезапуск mock; журнал ККТ |
| 403 «Снятие кассы» | Роль не accountant/admin | Так задумано |
| Проводки не появляются | Ошибка вставки | Логи api, `\d accounting_entries` |
| Webhook ЮKassa 401 | Неверная подпись | `YOOKASSA_WEBHOOK_SECRET` на сервере = в кабинете |
| Дубли от webhook | Идемпотентность не работает | Проверить `yookassa_webhook_events` |
| Дайджест не приходит | Email выкл / время | `/notify/settings`, digest_time, SMTP-тест |
| Чек не пробивается (в UI) | Смена закрыта / нет АТОЛ | Открыть смену, проверить настройки |

### 17.5. Сервер и инфраструктура

| Симптом | Причина | Решение |
|---|---|---|
| Медленные face/отчёты (10–60 с) | BLAS-потоки не ограничены | Установить `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` |
| «No services to build» в prod | Prod берёт готовый образ | Собрать через test-compose → `docker tag fitintel:test fitintel:prod` |
| БД «role does not exist» | Не `postgres`, а `fitnexus_user` | Использовать `fitnexus_user` |
| pg_dump пустой/ошибка | Пользователь/хост | `pg_dump -h 127.0.0.1 -U fitnexus_user` |
| API падает при старте | Миграции не применены | `alembic upgrade head` |
| Место на диске | Ротация не настроена | `deploy/backups`, `exports/` |
| 429 от nginx (не от API) | Rate-limit | Тюнинг `nginx.conf` |
| Grafana не пускает | admin/admin по умолчанию | Сменить через `GF_SECURITY_ADMIN_PASSWORD` |
| Алерты не приходят | Alertmanager receiver «null» | Настроить email/webhook |
| `backup.ps1` не работает на Linux | Это Windows-скрипт | На проде — volume `./backups` + `/ops/backup/run` |
| dev-compose не поднимается | Жёстко задан пароль БД | Сменить, не использовать для прода |
| HTTP 423 | Аккаунт заблокирован (5 попыток) | Подождать 5 мин или admin сбрасывает пароль |
| Кэш доступа пропускает уволенного | Кэш TTL 24 ч | `/ops` → инвалидация кэша по клиенту |

### 17.6. Интеграции

| Симптом | Причина | Решение |
|---|---|---|
| 1С: синхронизация 0 записей | Логин/пароль, роли в 1С, путь API V3 | Проверить журнал `connector_sync_log` |
| CRM «ХИТ» — ошибка «требуется документация» | Stub до получения спецификации | Ждать B-Office |
| Telegram 429 | Rate-limit 30/сек | Пауза |
| MAX не шлёт | `bot_token` не задан | «Интеграции» → max_messenger; `/messenger/max/sync` |
| MAX не принимает webhook | Webhook на «голый» IP локалки | Нужен домен с TLS |
| QR «Подпись недействительна» | Неверный `QR_SECRET_KEY` или истёк TTL | Проверить ключ, TTL |
| ITC СКУД 401 | Неверный Basic Auth | Проверить реестр (ITC_BASIC_USER/PASSWORD) |
| Kerong не открывает замок | Карта не в whitelist | Привязать карту в «Браслеты/Карты» |
| АТОЛ не отвечает | `dto_url`, сеть | Пинг `http://IP:16732`, «⚙ Настройки кассы» |
| ЮKassa возврат не приходит | `create_refund` UI не подключён | Через API |

### 17.7. Аудит и безопасность

| Симптом | Причина | Решение |
|---|---|---|
| Audit logs слишком много | Retention не настроен | «История → Срок хранения» (30/180/365/730/0) |
| Пароль ДТО ККТ виден | Открытый текст в БД | Ограничить доступ к `fiscal_settings` |
| Integration settings видны | Открытый текст в БД | TODO: шифровать (Fernet/Vault) |
| 403 на эндпоинт | Нет права | «Роли и права» → выдать право → сохранить |
| Guard-ошибка при сохранении ролей | Нет метода guard | Обновить сервер |
| 500 после входа (/auth/me) | Кривой email | Email обязателен `name@domain.ru` |

### 17.8. Сбор диагностической информации

| Что | Где |
|---|---|
| Логи API | `docker compose logs api --tail 100` |
| Логи desktop | `logs/client_*.log` (кнопка «Скопировать логи») |
| Логи DJ-агента | `E:\music\logs\agent_gui.log` |
| БД | `docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c "…"` |
| Health | `/health/`, `/ops/health`, `/metrics`, `/rbac/health` |
| Loki (все логи) | Grafana → Explore → `{container="deploy-api-1"}` |
| Скриншот | Помощь → «Скопировать логи» (кнопка в меню) |

### 17.9. Эскалация

**Помощь → Поддержка разработчика (MAX)** в desktop:

1. Открыть чат MAX
2. Описать проблему: экран → кнопка → ожидалось/получено
3. **«Скопировать логи»** (последние 40 строк)
4. Вставить в чат

**Email:** `support@fixintel.ru`

**Что включить в обращение:**
- Версия приложения (`FitIntel Pro v1.6.1`)
- Скриншот ошибки
- Логи
- Номер чека/смены (для кассовых инцидентов)
- Время инцидента

### 17.10. Восстановление после сбоя

**1. Проблема с БД:**

```bash
# Остановка API
docker compose -f docker-compose.test.yml stop api

# Восстановление
gunzip -c backups/db_YYYYMMDD.sql.gz | \
  docker compose -f docker-compose.test.yml exec -T db \
  psql -U fitnexus_user -d fitnexus_ai

# Запуск
docker compose -f docker-compose.test.yml start api

# Проверка
curl http://localhost/api/v1/health/
```

**2. Проблема с mpv:**

```bash
Get-Process mpv | Stop-Process -Force
# Перезапуск «Плеер: ВКЛ»
```

**3. Завис кэш доступа:**

```bash
curl -X POST http://IP/api/v1/ops/cache/clear -H "Authorization: Bearer $tok"
```

**4. Полный сброс (dev):**

```bash
docker compose -f docker-compose.test.yml down -v
docker compose -f docker-compose.test.yml up -d --build
# Инициализация заново
```

---

## 18. ПРИЛОЖЕНИЯ

### 18.1. Приложение А: Готовые SQL-запросы

**Список зон:**

```sql
SELECT id, name, provider_type, desired_state, machine_id
FROM music_zones ORDER BY name;
```

**Очистка мусора в музыке:**

```sql
DELETE FROM music_sfx WHERE name IS NULL OR path IS NULL OR path = '';
```

**Дубли сэмплов:**

```sql
DELETE FROM music_sfx a USING music_sfx b
WHERE a.id > b.id AND a.path = b.path;
```

**Список зон для агента:**

```sql
SELECT id, name, agent_token, machine_id, desired_state
FROM music_zones WHERE provider_type = 'local_agent';
```

**Миграция legacy enum в clients:**

```sql
UPDATE clients SET gender='MALE'  WHERE gender IN ('МУЖСКОЙ','мужской','М','m','male');
UPDATE clients SET gender='FEMALE' WHERE gender IN ('ЖЕНСКИЙ','женский','Ж','f','female');
UPDATE clients SET client_category='ADULT' WHERE client_category IN ('ОБЫЧНАЯ','REGULAR','regular');
UPDATE clients SET client_category='STAFF' WHERE client_category IN ('terminal','staff');
UPDATE clients SET status=UPPER(status) WHERE status <> UPPER(status);
UPDATE clients SET email=CONCAT('noemail-',LEFT(id::text,8),'@fitintel.local')
  WHERE email IS NULL OR email NOT LIKE '%@%';
```

**Пользователи с ролями:**

```sql
SELECT u.username, u.email, r.code AS role
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.id
LEFT JOIN roles r ON r.id = ur.role_id
WHERE u.is_active = TRUE
ORDER BY u.username;
```

**Проверка лицензии:**

```sql
SELECT id, key, machine_id, tariff, expires_at, is_first_login, plan, device_limit
FROM license_state;
```

**Email queue — застрявшие:**

```sql
SELECT recipient, subject, status, attempts, last_error, created_at
FROM email_queue
WHERE status <> 'SENT'
ORDER BY created_at DESC;
```

**Audit logs за сегодня:**

```sql
SELECT created_at, user_id, action, entity_type, entity_id
FROM audit_logs
WHERE created_at >= CURRENT_DATE
ORDER BY created_at DESC
LIMIT 100;
```

**Размер БД и таблиц:**

```sql
SELECT pg_size_pretty(pg_database_size('fitnexus_ai'));

SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 20;
```

### 18.2. Приложение Б: Переменные окружения (.env)

```ini
# ==============================================================
# deploy/.env — переменные окружения FitIntel Pro
# НЕ КОММИТИТЬ В GIT! Добавлен в .gitignore.
# ==============================================================

# === БАЗА ДАННЫХ ===
DATABASE_URL=postgresql+psycopg://fitnexus_user:password@localhost:5432/fitnexus_ai
POSTGRES_DB=fitnexus_ai
POSTGRES_USER=fitnexus_user
POSTGRES_PASSWORD=СложныйПарольМинимум16Символов

# === БЕЗОПАСНОСТЬ ===
SECRET_KEY=ДлиннаяСлучайнаяСтрокаМинимум32Символа
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
LICENSE_SECRET=test-only-заменить-в-проде
QR_SECRET_KEY=…
YOOKASSA_WEBHOOK_SECRET=…

# === СЕРВЕР ===
APP_NAME=FitIntel Pro
APP_VERSION=1.6.1
API_V1_PREFIX=/api/v1
HOST=0.0.0.0
PORT=8001
DEBUG=false
LOG_LEVEL=INFO
DOCS_ENABLED=true

# === CORS ===
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://club.example.ru"]

# === SMTP (клубный профиль) ===
SMTP_HOST=smtp.mail.ru
SMTP_PORT=465
SMTP_USER=club@mail.ru
SMTP_PASSWORD=ПарольПриложения

# === SMTP (системный профиль) ===
SYSTEM_SMTP_HOST=mail.fixintel.ru
SYSTEM_SMTP_PORT=465
SYSTEM_SMTP_USER=support@fixintel.ru
SYSTEM_SMTP_PASSWORD=…
SYSTEM_SMTP_FROM=support@fixintel.ru

# === SMS (smsc.ru) ===
SMSC_LOGIN=…
SMSC_PASSWORD=…
SMSC_SENDER=FitIntel

# === MAX Bot ===
MAX_BOT_TOKEN=…

# === Telegram ===
TELEGRAM_BOT_TOKEN=…

# === ЮKassa ===
YOOKASSA_SHOP_ID=…
YOOKASSA_SECRET_KEY=…
YOOKASSA_TEST_MODE=false

# === ККТ ===
ATOL_DTO_URL=http://192.168.1.50:16732

# === СКУД ITC ===
ITC_BASIC_USER=itc
ITC_BASIC_PASSWORD=itc_secret_2026

# === Redis ===
REDIS_HOST=redis
REDIS_PORT=6379

# === Мониторинг ===
SENTRY_DSN=…
GF_SECURITY_ADMIN_PASSWORD=…

# === BLAS-лимиты (для dlib/отчётов) ===
OPENBLAS_NUM_THREADS=1
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
```

### 18.3. Приложение В: Пример `.gitignore`

```gitignore
# ==============================================================
# .gitignore — FitIntel Pro
# ==============================================================

# === Бинари (не в git) ===
mpv/
tools/nssm.exe
*.exe
*.dll
*.7z
*.zip

# === Исключения — структура папок ===
!mpv/.gitkeep
!tools/.gitkeep

# === Сборка desktop ===
fitintel-desktop/dist/
fitintel-desktop/build/
fitintel-desktop/installer_out/
fitintel-desktop/build.log

# === Настройки (содержат токены) ===
fitintel-desktop/client_settings.json
fitintel-desktop/client_settings2.json
fitintel-desktop/connections.json
fitintel-desktop/connections2.json
fitintel-desktop/rfid_uid_cache.json
fitintel-desktop/rfid_widget_pos.json

# === Киоск-режим ===
fitintel-desktop/shop_products.json
fitintel-desktop/shop_sales.json
fitintel-desktop/shop_settings.json
fitintel-desktop/shop_photos/

# === Логи ===
logs/
*.log

# === Python ===
__pycache__/
*.py[cod]
.venv/
.venv-desktop/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# === Секреты ===
.env
.env.*
!.env.example
!env.example

# === Иконки (кэш) ===
fitintel-desktop/assets/icons-generated/

# === Разное ===
.DS_Store
Thumbs.db
*.bak
*.tmp
```

### 18.4. Приложение Г: Горячие клавиши

| Клавиша | Действие |
|---|---|
| **F1** | Инструкция по текущему экрану |
| **F5** | Обновить данные |
| **F11** | Табло с часами (полный экран) |
| **Ctrl + Q** | Выход из программы |
| **Ctrl + +** | Увеличить шрифт |
| **Ctrl + −** | Уменьшить шрифт |
| **Ctrl + A** | Выделить всё (в поле ввода) |
| **Ctrl + C** | Копировать |
| **Ctrl + V** | Вставить |
| **Enter** | Подтвердить (в формах) |
| **Esc** | Закрыть окно/диалог |

### 18.5. Приложение Д: Список всех ~191+ эндпоинтов (сводка по группам)

| Группа | Кол-во |
|---|---|
| Auth / RBAC | 22 |
| Клиенты / Абонементы / Визиты | 20 |
| Доступ / СКУД / Face ID | 30 |
| Платежи / Касса / Онлайн | 40 |
| Бухгалтерия / Отчёты / Экспорт | 25 |
| Аналитика / AI | 12 |
| Коммуникации | 25 |
| Документы / Коммерция / Видео | 20 |
| Система / Setup / Ops | 20 |
| Музыка / DJ | 17 |
| **Итого** | **231** (с учётом мультиметодных) |

**Примечание:** реально ~191+ уникальных путей (некоторые пути с несколькими методами — GET/POST/PATCH/DELETE — считаются как один).

### 18.6. Приложение Е: Список всех ролей и прав

**9 ролей:**

1. `superadmin` — SuperAdmin (bypass)
2. `admin` — Администратор (71 право)
3. `owner` — Владелец (2 права)
4. `manager` — Менеджер (13+)
5. `cashier` — Кассир (6+)
6. `accountant` — Бухгалтер (0 — выдать!)
7. `trainer` — Тренер (3)
8. `client` — Клиент (0)
9. `device` — Устройство (0)

**Формат прав:** `объект.действие` — 51 уникальное право.

**Основные:**
- `system.admin`, `users.*`, `roles.*`, `permissions.*`, `audit.*`
- `clients.*`, `subscriptions.*`, `tariffs.*`, `services.*`
- `visits.*`, `access.*`, `credentials.*`, `lockers.*`, `face.*`
- `payments.*`, `wallet.*`, `cash_desk.*`, `receipts.*`, `sales.*`
- `documents.*`, `reports.*`, `accounting.*`, `exports.*`
- `club_settings.*`, `settings.*`, `setup.*`, `ui-config.*`

### 18.7. Приложение Ж: Структура БД (сводка)

**PostgreSQL таблиц:** ~65
**SQLite таблиц (внутренняя учётка):** ~5

**Ключевые группы:**

| Группа | Таблиц |
|---|---|
| Пользователи/RBAC | 6 (users, roles, permissions, user_roles, role_permissions, ui_screens) |
| Матрица экранов | 1 (ui_role_screens) |
| Клиенты | 3 (clients, client_events, client_verification) |
| Абонементы | 2 (subscriptions, subscription_events) |
| Тарифы | 1 (tariffs) |
| Визиты | 1 (visits) |
| Доступ | 5 (credentials, dynamic_qr_codes, lockers, locker_sessions, locker_privileges) |
| Кошелёк | 2 (wallets, wallet_transactions) |
| Платежи | 4 (payments, receipts, payment_refunds, fiscal_receipts) |
| Касса | 3 (fiscal_shift, fiscal_pending, fiscal_settings) |
| Бухгалтерия | 1 (accounting_entries) |
| Face ID | 1 (face_id_records) |
| Документы | 3 (documents, document_events, document_templates) |
| Аудит | 1 (audit_logs) |
| Лицензия | 1 (license_state) |
| DAL | 3 (dal_drivers, dal_devices, dal_events) |
| Музыка | 4 (music_zones, music_playlists, music_sfx, music_pad_events) |
| Уведомления | 3 (email_queue, notification_settings, notification_log) |
| Интеграции | 3 (integration_settings, external_sync_log, connectors) |
| Платежи онлайн | 2 (yookassa_webhook_events, recurring_schedules) |
| Feature flags | 3 (feature_flags, ff_rollouts, ff_license_binds) |
| Прочее | ~20 |

### 18.8. Приложение З: Схема папок внутри сборки

**`FitIntelDesktop.exe` (onefile) распаковывается в `%TEMP%\_MEIxxxxx/`:**

```
_MEIxxxxx/
├── FitIntelDesktop.exe       # Сам GUI
├── mpv/
│   ├── mpv.exe              # 120 МБ
│   ├── mpv.com
│   └── d3dcompiler_43.dll
├── tools/
│   └── nssm.exe
├── scripts/music/           # DJ-агент
│   ├── agent.py, deck.py, pads.py, duck.py, skud_trigger.py
│   └── fitintel_player_agent.py
├── assets/                  # Иконки
│   ├── app_icon_512.png, app_icon_1024.png
│   ├── fitintel.ico, FitIntel_icon.ico
│   └── ...
├── windows/                 # Все экраны (*_tab.py)
├── api/client.py
├── rfid/                    # RFID-операции
└── PyQt6/, cv2/, smartcard/ # Зависимости
```

### 18.9. Приложение И: Инструкция по установке на чистый ПК

**Шаг 1. Установка сервера (Ubuntu):**

```bash
# См. раздел 12.10 — 7 шагов
```

**Шаг 2. Установка desktop (Windows):**

```powershell
# 1. Скопировать FitIntelDesktop-Setup_v1.6.1.exe
# 2. Запустить
# 3. Диалог «Адрес сервера клуба» → http://IP/api/v1
# 4. Завершить установку
```

**Шаг 3. Первый запуск:**

1. Логин/пароль (superadmin / из лицензии)
2. Смена пароля
3. Вход

**Шаг 4. Настройка музыки:**

1. «Музыка/DJ» → «⏵ Плеер: ВКЛ»
2. «⚙ Плеер…» → указать `lib` (папка с музыкой)
3. «Папка на A…» → выбрать папку
4. «Применить пульт»

**Шаг 5. Настройка кассы:**

1. «Бухгалтерия → Платежи → ⚙ Настройки кассы»
2. Драйвер (АТОЛ), адрес `http://IP:16732`, ОФД
3. «🔓 Открыть смену»

**Шаг 6. Настройка Face ID:**

1. «Face ID» → «Настройки движка…»
2. Порог уверенности, мин. качество, лимит шаблонов, хранение фото
3. «📷 Снять с камеры» → «📸 Снять» → «Сохранить»

**Шаг 7. Настройка СКУД:**

1. Реестр Windows: `HKLM\SOFTWARE\ITCService` → URL API
2. `Restart-Service ITCService`
3. Проверка: `curl -u itc:itc_secret_2026 http://IP:8001/api/v1/skud/health_check`

**Шаг 8. Уведомления:**

1. «Уведомления → Email» → SMTP хост, порт, логин, пароль приложения
2. «Сохранить Email»
3. «Отправка» → тест на свой email

---

## ЗАКЛЮЧЕНИЕ

**FitIntel Pro v1.6.1** — Production Ready.

**Документация содержит:**

- 17 вкладок desktop (sidebar)
- 63 подвкладки первого уровня
- 8 подвкладок второго уровня
- 11 отдельных окон
- ~99 уникальных экранов всего
- ~191+ API эндпоинтов
- ~50 SQLAlchemy моделей
- 9 ролей RBAC, 51 разрешение
- 7 hardware драйверов
- 4 файла зависимостей
- 3 основных компонента (Backend, Desktop, DJ-агент)

- **Часть 1** — Разделы 1–4 (Общие сведения, Архитектура, Стек, Структура)
- **Часть 2** — Разделы 5–6 (Зависимости, Модели данных)
- **Часть 3** — Разделы 7–8 (API Reference 191, RBAC)
- **Часть 4** — Разделы 9–11 (HAL, Сервисы, Музыкальный модуль)
- **Часть 5** — Разделы 12–16 (Инфраструктура, Команды, Безопасность, Интеграции, Мониторинг)
- **Часть 6** — Разделы 17–18 (Устранение неполадок, Приложения) **← этот ответ**

**Поддержка:** `support@fixintel.ru` (Помощь → Поддержка разработчика MAX)

**Лицензия:** Проприетарная (ИП Санакин А.В.)

---

**Конец документа.**

*Версия документа 1.7.2 | Версия приложения 1.6.1 | Октябрь 2026*

