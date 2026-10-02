# Руководство администратора

## 1. Мастер установки (экран «Мастер установки», таблица setup_wizard)

Порядок строгий (шаг N требует шаг N−1): **database → license (ОБЯЗАТЕЛЬНО) → admin → club → devices → tariffs → complete**. Без лицензии ПО блокируется (403 на API), завершить настройку нельзя.
- `/setup/license/activate` — ключ проверяется (Ed25519), активируется привязка к machine-id; ответ содержит **пароль superadmin из ключа** — сохраните!
- Первый вход superadmin → принудительная смена пароля (флаг force_change_password; сбрасывается вместе с license_state.is_first_login).
- «Настройки» мастера редактируют `deploy/.env` (категории: general/security/database/redis/cors/celery/monitoring/email/sms/telegram/max/one_c/webhooks; чувствительные маскируются); «Тест соединения» — postgres/redis/smtp/max/sms/telegram/1c.
- Импорт/экспорт настроек, валидация конфигурации, сброс мастера (`/setup/reset`, требует confirmation).

## 2. Пользователи, роли, права

- «Пользователи»: CRUD, деактивация, сброс пароля (с флагом force_password_change), назначение/снятие ролей (право `roles.manage`). superadmin удалить нельзя.
- «Роли и права»: матрица RBAC. Итоговые права = объединение прав всех ролей пользователя (дедуп по коду). Диагностика: `GET /rbac/check-access|explain-access|debug-access`, health — `/rbac/health`.
- «Экраны ролей» (ui_config): 9 ролей, реестр `ui_screens`, матрица `ui_role_screens`. **Строгая модель**: пустая строка роли = пользователь не видит ни одного экрана; у superadmin экран `ui_config` защищён; «Сбросить к умолчанию» вернёт DEFAULT_PROFILES.
- Аудит «История»: фильтры (entity/action/actor/период), **retention_days** (0 = бессрочно), автоочистка при чтении.

## 3. Касса и оборудование

- **Настройки кассы** (desktop, admin): `fiscal_settings` — драйвер + `dto_url/dto_login/dto_password` + ОФД. Боевая АТОЛ: ДТО 10 на `http://IP:16732`. Тестовый mock — `http://<VM>:18004` (сквозная нумерация ФД, state-файл).
- **Универсальные адаптеры** (`app/services/fiscal/`): АТОЛ (poll /results), Штрих-М (Web JSON v2), Эвотор (Cloud), Меркурий (InfoSoft) — выбор через `FiscalManager(config)['active']`; health-check всех: `health_check_all()`.
- **Эквайринг** (`app/services/bank/`): Сбер (sbrf.dll ctypes или REST register.do), Тинькофф (подпись SHA-256 отсортированных полей+password), Райффайзен (заготовка) — `BankManager(config)`.
- **DAL** («Устройства»): репозиторий пакетов `.fnp` (АТОЛ 30Ф, Штрих-ON-LINE, весы Mercury, терминал Hikvision, сканер Zebra), install/enable/disable/upgrade/delete, автообнаружение, ping, команды, журнал `dal_events`.
- **SKUD ITC** (`/skud/*`, Basic Auth из env ITC_BASIC_USER/PASSWORD): checkaccess (карта/QR/солярий/аква), контроль выхода с шкафчиками, события → visits.
- **Kerong offline**: `/kerong/auth` (проверка карты), `/kerong/sync` (раз в 5 мин список авторизованных карт), модели KR-S50…KR-PRO.
- **Face ID**: настройки клуба `/face-id/settings` (threshold 0.1–1.5, min_quality, max_templates 1–20, store_photos); фото хранятся в volume `face_photos` (chmod 600) только если включено; анти-спуфинг (FFT-анализ экрана) и liveness (моргание, EAR) — задел.

## 4. Деньги: онлайн-оплаты и автоплатежи

- **ЮKassa**: env `YOOKASSA_SHOP_ID/SECRET_KEY/WEBHOOK_SECRET`, `YOOKASSA_TEST_MODE`. Webhook `/yookassa/webhook` — проверка HMAC-подписи, идемпотентность по `event_key`; succeeded → платёж + ФН + пополнение кошелька + активация абонемента (metadata.subscription_id). Возвраты с контролем суммы; сохранённые карты; `/yookassa/auto-charge/run` — автопродление с сохранённой карты.
- **Рекурренты** (`/recurring/*`): расписания day/week/month, пауза/возобновление/отмена, ретраи с экспоненциальной паузой (2^attempt часов, max_retries), история списаний, тестовый «fail-next».
- **СБП** (`sbp_service`): mock-режим (генерация QR, статусы, rebill-токены).

## 5. Интеграции внешних систем

- **1С:Фитнес клуб** (API V3): «Интеграции → Внешние системы»: адрес `http://<сервер-1С>/<база>/hs/api3`, логин/пароль (роли в 1С: «Удалённый доступ внешнее приложение» + «Запуск внешнего соединения»). Синхронизация: клиенты (поиск по телефону, обновление без дублей) → абонементы (тарифы-импорты IMP_*) → визиты (дедуп по времени). Журнал «📋 Журнал».
- **CRM «ХИТ» (B-Office)**: интерфейс готов, ждёт документацию REST API от вендора.
- **A&A**: импорт/экспорт CSV, webhook `/aa/webhook`, журнал.
- **CommerceML 2.0** (`accounting/onec_integration.py`): режимы file/http/mock; выгрузка каталога/контрагентов/документов (windows-1251), импорт offers/заказов, OData-чтение/создание документов.
- **MAX/Telegram боты**: токены в env (`MAX_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`); rate-limit 30/сек; FSM-сценарий записи (`/max-bot/fsm`); привязки client↔chat; cron-напоминания.

## 6. Надёжность и эксплуатация

**Бэкапы (два пути):**
- Windows-хост: `deploy/backup/backup.ps1` (pg_dump на 127.0.0.1, пароль из `FITINTEL_DB_PASSWORD`,
  ротация 14 дней → `backups/`); восстановление — `restore.ps1 backup_YYYYMMDD_HHMMSS.sql`.
- Linux/прод: каталог `./backups` (volume db) + API-задача `POST /ops/backup/run`
  (pg_dump, fallback — каталог-таблицы), ротация настраивается в `/ops/backup/config`.

**Мониторинг:** стек Prometheus + Grafana + Loki + Promtail + node-exporter + cAdvisor + Alertmanager
(`deploy/monitoring/docker-compose.monitoring.yml`). Дашборды: FitIntel API (RPS, 5xx%, p95, топ путей,
логи Loki), System. **Alertmanager сейчас с заглушкой receiver "null" — подключите email/webhook.**
Grafana по умолчанию admin/admin — сменить сразу. Расширенный health: `/health/` (БД) и
`/ops/health` (БД + диск + память + последний бэкап).

**env.example:** образец `deploy/.env` со всеми переменными по категориям — в репозитории (deploy/env.example).


- **Бэкапы**: `deploy/backup/` (host-скрипт + `/ops/backup/run` через API: pg_dump, fallback — каталог-таблиц; ротация, восстановление). В prod дампы пишутся в `./backups` (volume db). Репликация: single-node (заготовка под HA).
- **Мониторинг**: `/metrics`, `/health`, `/ops/health`; Sentry DSN в env.
- **Feature flags** (`/feature-flags/*`): percentage/canary rollout (MD5-бакет user:flag), привязка к фичам лицензии, статистика оценок, WebSocket-пуши (`/feature-flags/stream`).
- **Уведомления** (`/notify/*`): SMTP (SSL/TLS), SMS smsc.ru, Web Push (VAPID), журнал, авто-дайджест ежедневно в digest_time (поток-планировщик внутри API).
- **Обновление**: `git pull` → `docker compose build` (test) или пересборка образа `fitintel:prod` + `docker load`; desktop — новый Setup поверх. Хеши релизов — RELEASES.md.

## 6а. Дополнительные модули (кратко)

- **Документы E33:** генерация PDF/DOCX прямо в коде (без LibreOffice), подписание (простое и ЭП «CAdES-эмуляция»),
  массовая генерация по списку клиентов (`/documents/mass-generate`), реестр подписей сторон,
  связи (абонемент/платёж/договор/визит), сводная история. Шаблоны — `{{client_name}}`, `{{date}}`…
- **Коммерция:** тарифные планы и модули (`/commercial/plans`, калькулятор цены), подписки клуба
  (trial, upgrade), white-label (`/brand/settings`), тенанты сетей (`/brand/tenants`).
- **Видеоаналитика E12/E45:** триггеры (intrusion/loitering/crowd/fall/tailgating) с порогом уверенности,
  feedback-loop: «ложная тревога» дообучает триггер (порог +0.005); ONVIF-автообнаружение (эмуляция),
  алерты камер с подтверждением/false-positive, архив 30 дней.
- **Самообучение E60:** `/self-learn/pricing/analyze|apply` (рекомендации цен тарифов),
  `/self-learn/self-heal` (самоисцеление БД), churn-анализ (batch).
- **Подтверждение телефона:** `/phone-verify/*` (smsru/twilio/whatsapp + Telegram только при привязке,
  fallback-цепочка, TTL 5 мин, 5 попыток) и `/clients/verify-phone/*` (код через push MAX).
- **Real-time:** SSE `/sse/live/{club}` (дашборд, 30 с), WebSocket `/ws/alerts`, `/feature-flags/stream`.
- **Печать:** `/print/*` — очередь заданий, режимы gdi/escpos/emulate.
- **RFID-ридер:** `/reader/*` — PC/SC: detect-card, read/write block (16 байт), read-sector (408 без карты).

## 7. Рекомендации

- Ежедневно: закрытие смены + сверка; еженедельно: проверка бэкапов (тестовое восстановление); ежемесячно: ротация ключей, аудит retention, контроль лимитов лицензии (`/license/limits`).
- Не храните пароль ДТО вне БД; ограничьте доступ к `deploy/.env` и volume'ам.
