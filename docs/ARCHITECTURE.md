# Архитектура FitIntel Pro

## Общая схема (прод, docker-compose.prod.yml)

```
                        ┌─ nginx:80 (TLS-заготовка: 443 закомментирован)
Клиенты / SKUD / боты ──┤
                        └─ api (fitintel:prod) ── celery-worker (Redis broker)
                               │        │
                          postgres:16  redis:7 (кэш/брокер, allkeys-lru 256МБ)
                               │        │
                        volumes: postgres_prod, face_photos, ./backups

ККТ АТОЛ (ДТО 10, :16732) и mock (:18004) — вне compose, доступ по сети клуба.

**Nginx** (deploy/nginx): тест — plain :80 → api:8000; прод — редирект 80→443, TLS 1.2/1.3,
rate-limit: API 10 r/s (burst 20), `/auth/login|token` 5 r/min (burst 5).

**Мониторинг** (deploy/monitoring, отдельный compose, сеть deploy_backend):
Prometheus v2.51 (retention 30 дней) → метрики API `/metrics` + node-exporter + cAdvisor;
Loki + Promtail (docker_sd, логи всех контейнеров); Grafana 10.4 (дашборды fitintel-api/system,
логи из Loki); Alertmanager — **receiver "null" (заглушка, настройте свой!)**.
Алерты (prometheus/rules/fitintel.yml): HighErrorRate (5xx>0.1/s, 2м, critical),
HighLatency (p95>0.2с, 5м), APIDown, DiskSpaceLow (<10%), MemoryHigh (<10%), PostgreSQLDown.


Важно из compose.prod: образ грузится архивом (`docker load -i`), секреты обязательны в `deploy/.env` (`POSTGRES_PASSWORD:?`), лимиты BLAS-потоков `OPENBLAS/OMP/MKL_NUM_THREADS=1` (иначе dlib/отчёты висят 10–60 с).

## Слои кода

- `app/api/v1/*.py` — тонкие роутеры: валидация схем (Pydantic), права (`require_permission`/`require_roles`), вызов сервисов, аудит.
- `app/services/*.py` — бизнес-логика и транзакции; `accounting/`, `bank/`, `fiscal/`, `connectors/` — подпакеты-адаптеры.
- `app/repositories/` — доступ к данным; модели в `app/models/`.

## Ключевые потоки

**Платёж (E33):** `POST /payments/` (PENDING) → `POST /payments/{id}/complete` → **сначала чек** `_fiscalize` (guard смены на сервере → ДТО 10 `sell`) → COMPLETED + `completed_at` → автопроводка `accounting_entries` (Дт 50/57 Кт 90.1) → баланс смены.
**Смена кассы:** состояние в БД (`fiscal_shift`, строка на каждое открытие); обороты закрытия → `fiscal_pending`; обнуление — `/fiscal/cash-withdrawal` (admin/superadmin/accountant/бухгалтер).
**Вход клиента:** идентификатор (client_id → RFID → FaceID → QR) → credential ACTIVE и не просрочен → активный абонемент (статус/лимит/временное окно FULLDAY/DAYTIME/NIGHTTIME) → списание визита → visit ACTIVE; выход: длительность, авто-освобождение шкафчика; SKUD дополнительно блокирует выход при закрытом бесплатном шкафчике.
**Онлайн-оплата ЮKassa:** create → redirect → webhook (HMAC-подпись, идемпотентность по event_key) → succeeded: платёж + фискальный номер + пополнение кошелька + активация абонемента из metadata.
**Синхронизация 1С:** коннектор `fitness1c` (HTTP API V3: /clients /subscriptions /visits /schedule) → нормализация → sync_engine с дедупликацией (клиенты — по телефону, визиты — по паре client+entry_time, тарифы автосоздаются IMP_*) → журнал `connector_sync_log`. CRM «ХИТ» — stub (нужна документация B-Office).

## Адаптеры (подменяемые реализации)

| Подсистема | Интерфейс | Реализации | Выбор |
|---|---|---|---|
| Кассы | `BaseFiscalPrinter` | AtolAdapter (ДТО 10, poll /results), ShtrihAdapter (Web Server JSON v2), EvotorAdapter (Cloud), MercuryAdapter (InfoSoft) | `FiscalManager(config)` — `config['active']` |
| Банки | `BaseBankTerminal` | SberbankAdapter (sbrf.dll ctypes / REST register.do), TinkoffAdapter (Init/Cancel/Confirm, подпись SHA-256 отсортированных полей+password), RaiffAdapter (mock-заготовка) | `BankManager(config)['active']` |
| Клубные системы | `ClubConnector` | Fitness1CConnector (API V3), HitConnectorStub | `get_connector(type, url, login, pwd)` |

## База данных (основное)

PostgreSQL: clients, users, roles/permissions/user_roles/role_permissions (RBAC), payments(+completed_at), subscriptions(+frozen_at/until, events история), visits, credentials (QR/RFID/CARD/BRACELET/MOBILE_KEY/ONLINE_LOCK/FACE_ID), wallets(+frozen_balance)/wallet_transactions, lockers/locker_sessions, fiscal_receipts, fiscal_shift, fiscal_pending, fiscal_settings, accounting_entries (entry_date, Дт, Кт, amount, source), service_bookings, trainer_* (profiles/schedules/bookings/sales/kpi), online_sessions/participants, messenger_* (chats/messages/bindings/notifications/settings), dynamic_qr_codes, audit_logs(+retention_days), license_state, ui_screens/ui_role_screens, feature_flags/ff_rollouts/ff_license_binds/ff_evaluations, recurring_schedules/charges, referral_codes/referrals/referral_rewards, payroll_records, export_log/data_export_jobs, dal_drivers/dal_devices/dal_events, yookassa_webhook_events, saved_cards, payment_refunds, notification_settings/log, webpush_subscriptions, bot_sessions/bot_bookings, telegram_links, max_links, setup_wizard, connectors, employee_shifts, widget_settings/widget_bookings.

SQLite (отдельный файл `fitintel_accounting.db`): внутренняя учётка InternalAccounting — accounts, entries, contragents, items, balances (ПКО/РКО/реализация/поступление/ОСВ/P&L/баланс/ДДС/акт сверки).

## Безопасность

- JWT; блокировка после 5 неверных паролей; superadmin: при первом входе флаг `force_change_password` (login) → смена пароля сбрасывает `license_state.is_first_login` (UPSERT, иначе «вечный круг»).
- RBAC: права (`require_permissions`, аудит denied/allowed), роли (`require_roles`), superadmin bypass; health: `GET /rbac/health`.
- Экраны тонкого клиента — **строгая модель**: `ui_role_screens`, ничего не отмечено = пользователь не видит ни одного экрана; у superadmin экран `ui_config` нельзя скрыть.
- Лицензии: Ed25519 (`FIPRO-<b64>.<sig>`), одноразовая привязка к `machine-id`; активация ставит пароль superadmin из ключа; soft/hard-режим (hard — блок при превышении max_clients).
- Rate limit: 30 запросов/сек к Telegram и MAX API (429).
- Пароли ДТО и токены — в `fiscal_settings`/env; чувствительные env-поля маскируются в `/setup/settings` (`****`).

## Фоновые задачи

- `AnalyticsScheduler` (APScheduler, в процессе API): ежедневно 00:05 — пересчёт агрегатов за вчера + прогнозы (attendance/revenue/new_clients/churn_risk) на 7 дней.
- Celery: авто-истечение абонементов (`subscription_lifecycle`), иные периодические задачи.
- Дайджест уведомлений: поток-планировщик в API, ежедневно в `digest_time` (env).
- `/auto/run-daily` — «кнопка автоматики»: напоминания о визитах/продлении по ML-журналу.
- Кэш доступа (`access_cache`): TTL 24 ч, версионирование по device_id, инвалидация при изменении прав; refresh_all_caches/cleanup_expired_cache.

## Аутентификация (детали)

5 неверных паролей → блокировка 5 минут (HTTP 423, счётчик сбрасывается при успехе).
Первый созданный пользователь автоматически получает роль SUPER_ADMIN.
Хардкод: роли admin добавляется право `devices.create`.

## Desktop-клиент

`ApiClient` (api/client.py): requests-сессия, таймаут 10 с, `_e55_*` helpers (привязаны к классу), авто-перелогин при 401 (E70, по saved_login из client_settings.json). Вкладки `windows/*_tab.py`; F1-инструкции `help_dialog.py`; сборка PyInstaller `FitIntelDesktop.spec` (абсолютные пути), установщик `installer.iss`. Версия — в 4 файлах + `#define MyAppVersion`.
