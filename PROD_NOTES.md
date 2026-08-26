# PROD_NOTES.md — что важно помнить перед продом

## E1 — Общая архитектура (ТЗ §1)

**Что важно помнить:**
- Стек: FastAPI + SQLAlchemy 2.0 + PostgreSQL 14+ + psycopg (v3) + Pydantic v2.
- Структура: `app/api/v1/` — роутеры, `app/services/` — бизнес-логика, `app/core/` — конфиг, `fitintel-desktop/` — PyQt6 тонкий клиент.
- Базовый префикс API: `/api/v1` (настраивается в `.env` через `API_V1_PREFIX`).
- CORS: `BACKEND_CORS_ORIGINS` в `.env` — обязательно указать продакшен-домен.

**Оговорки по тестам / эмуляция:**
- `DOCS_ENABLED=true` в dev; в проде отключить (`false`) или закрыть basic-auth.
- `MAINTENANCE_MODE` — заглушка, middleware не реализовано полностью.

## E2 — Аутентификация и авторизация (ТЗ §2)

**Что важно помнить:**
- JWT: `SECRET_KEY` в `.env` (HS256), `ACCESS_TOKEN_EXPIRE_MINUTES=30`, `REFRESH_TOKEN_EXPIRE_DAYS=7`.
- Роли: superadmin, admin, manager, trainer, reception (E51 расширяет матрицей экранов).
- Эндпоинты: `/auth/login` (JSON), `/auth/refresh`, `/auth/me`.
- Пароли хранятся хешированными (bcrypt).

**Оговорки по тестам / эмуляция:**
- Legacy `/auth/token` (form-data) сохранён для совместимости; тонкий клиент переключён на JSON `/auth/login` (E52).
- RBAC на уровне эндпоинтов — через `Depends(require_permission(...))` или `Depends(get_current_user)`; не все роутеры покрыты (E56, E34 и др. — доработать).

## E3 — Клиенты (ТЗ §3)

**Что важно помнить:**
- Таблица `clients`: `first_name`, `last_name`, `middle_name`, `phone` (UNIQUE), `email`, `birth_date`, `gender` (enum: MALE/FEMALE/НЕ_УКАЗАН), `client_category` (enum: ADULT/CHILD/VIP/STAFF/...), `status` (ACTIVE/INACTIVE/BLOCKED).
- Импорт из A&A: `/aa/import-csv` (E21) — автоподстановка enum, парсинг ФИО из одной колонки.
- Поиск и фильтрация через `/clients` (query params).

**Оговорки по тестам / эмуляция:**
- Legacy-данные в БД могли содержать значения вне enum (МУЖСКОЙ, ОБЫЧНАЯ, REGULAR) — мигрировано в E52, но новый импорт должен нормализовать через `_norm_gender/_norm_category` (E21).
- `email` NOT NULL: legacy NULL заменены на `noemail-{id}@fitintel.local`.

## E4 — Абонементы и тарифы (ТЗ §4.1–4.3)

**Что важно помнить:**
- Таблицы: `tariffs` (услуги/периоды/цены), `subscriptions` (привязка к клиенту, start_date/end_date, status).
- Статусы подписки: active, paused, expired, cancelled.
- Автопроверка срока: `/subscriptions/expiring` + `/subscriptions/inactive`.

**Оговорки по тестам / эмуляция:**
- Заморозка подписки (freeze) — статус frozen в БД, логика в терминале (E35); полноценный freeze_reason/frozen_at добавлены в схему.
- Рекуррентные списания — см. E36.

## E5 — Посещения (ТЗ §4.4)

**Что важно помнить:**
- Таблица `visits`: `client_id`, `visit_date`/`visited_at`, `status` (planned/completed/cancelled/no_show).
- Check-in: POST `/visits/check-in` (связь с Face ID E12/E45).
- История визитов — основа для аналитики (churn, heatmap E44).

**Оговорки по тестам / эмуляция:**
- Колонка даты адаптивная: `visited_at`/`visit_date`/`check_in_at`/`created_at`/`start_time` — E44 пытается угадать имя.
- Тип колонки может быть `timestamptz` или `VARCHAR` — heatmap (E44) фильтрует в Python.

## E6 — Расписание и бронирование (ТЗ §4.5)

**Что важно помнить:**
- Таблицы: `schedule` (расписание тренеров/услуг), `service_bookings` (брони).
- Бронирование через тонкий клиент и MAX Bot (E46).
- Widget бронирования (E41) — публичные слоты без авторизации.

**Оговорки по тестам / эмуляция:**
- Слоты в widget (E41) фиксированы 09:00–20:00, не связаны с реальным schedule.
- Конфликты бронирования — проверка на точное совпадение slot_datetime; в проде нужна интервальная проверка + max_capacity.

## E7 — Автобэкап PostgreSQL (ТЗ §9, E10)

**Что важно помнить:**
- Скрипт: `scripts/backup_postgres.py` — pg_dump + gzip.
- Планировщик: APScheduler в `app/main.py` (cron `0 3 * * *`).
- Ротация: 30 дней (`backups/postgres/`).
- Пароль читается из `.env` (`POSTGRES_PASSWORD`).

**Оговорки по тестам / эмуляция:**
- На dev-машине без pg_dump в PATH — mode="catalog" (только список таблиц).
- Бэкап НЕ включает Redis/файлы загрузок — только PostgreSQL.

## E8 — Ротация секретов (ТЗ §9)

**Что важно помнить:**
- `.env` добавлен в `.gitignore` (E8 выполнено).
- Перед продом: сменить `SECRET_KEY`, `POSTGRES_PASSWORD`, `SMTP_PASSWORD`, `LICENSE_SECRET` — старые значения были в git-истории.
- JWT-токены инвалидируются при смене `SECRET_KEY`.

**Оговорки по тестам / эмуляция:**
- `LICENSE_SECRET` в `.env` — дефолт test-only; в проде использовать сильный ключ.
- Integration settings (E56) хранятся в БД открытым текстом — перед продом шифровать (Fernet/Vault).

## E9 — Мониторинг и health-check (ТЗ §9)

**Что важно помнить:**
- Базовый: `GET /api/v1/health/` — всегда 200.
- Расширенный: `GET /api/v1/health/extended` (E9) — проверяет PostgreSQL, диск, память, дату последнего бэкапа.
- Логи: `logs/` directory, уровень `LOG_LEVEL` из `.env`.

**Оговорки по тестам / эмуляция:**
- Redis-кэш для health НЕ используется — все проверки синхронные.
- Нет алертинга (Telegram/PagerDuty) — только endpoint.

## E10 — Развёртывание (ТЗ §9)

**Что важно помнить:**
- Файл `PROD_NOTES.md` (этот документ) — единая точка входа.
- Прод: `uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4`.
- Тонкий клиент: `cd fitintel-desktop && python main.py`.
- Системные требования: 4 GB RAM, 20 GB SSD, PostgreSQL 14+.

**Оговорки по тестам / эмуляция:**
- Нет Docker-файла — ручное развёртывание.
- Нет CI/CD pipeline — деплой через git pull + restart.

## E11 — Платежи (ТЗ §4.6)

**Что важно помнить:**
- Таблица `payments`: `client_id`, `amount`, `method` (cash/card/transfer/yookassa), `status` (pending/completed/failed/refunded).
- Интеграция YooKassa: E26 (отдельный модуль).
- Возврат: POST `/payments/{id}/refund` (E55).

**Оговорки по тестам / эмуляция:**
- Статус CANCELLED отсутствует — кнопка «Отмена» в UI делает refund (E55). Для прода завести отдельный статус.
- Автопроводки в бухгалтерию (E32) — ручные триггеры, не автоматические.

## E12 — Face ID / Биометрия (ТЗ §5)

**Что важно помнить:**
- Таблица `face_id_records`: `client_id`, `face_encoding`, `photo` (base64 или путь).
- Эндпоинты: `/face-id/enroll`, `/face-id/verify`, `/face-id/anti-spoofing`.
- В ПРОДЕ — ТОЛЬКО self-hosted распознавание (свой сервис). НЕ FindFace/NtechLab, НЕ Face++ cloud — лицензии и 152-ФЗ.

**Оговорки по тестам / эмуляция:**
- Verify принимает `{"photo": base64}` (не face_encoding). Тест шлёт 1x1 пиксель.
- Anti-spoofing — заглушка; в проде — liveness detection.
- Терминал (E35) использует эмуляцию Face ID (точное сравнение строк).

## E13 — MAX Bot / Мессенджер (ТЗ §15)

**Что важно помнить:**
- MAX API: база `https://platform-api.max.ru`, токен в заголовке `Authorization`.
- Бота может создать только верифицированное юрлицо РФ («MAX для бизнеса»).
- Webhook: HTTPS с доверенным сертификатом (в dev — Long Polling `platform-api2.max.ru`).

**Оговорки по тестам / эмуляция:**
- FSM (E46) — ядро бронирования без транспорта; сообщения через POST `/max-bot/fsm/message`.
- Клавиатуры — массивы строк JSON (структура не подтверждена боевым API MAX).
- Рассылки (E57) — ручная привязка client_id ↔ max_user_id.

## E14 — Email / SMTP (ТЗ §15.2)

**Что важно помнить:**
- Настройки в `.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`.
- Отправка через `smtplib` (E17 дайджест, E34 рассылки).
- `SMTP_FROM_NAME` / `SMTP_FROM_EMAIL` — брендинг.

**Оговорки по тестам / эмуляция:**
- SendGrid/Mailchimp — эмуляция (E34), реальные API-ключи в `.env`.
- Email в документах (E33) — эмуляция, ничего не отправляется.

## E15 — Устройства и оборудование (ТЗ §6, E23, E47)

**Что важно помнить:**
- Таблицы: `equipment` / `devices` (legacy), `dal_drivers` / `dal_devices` (E47 DAL).
- Протоколы: Modbus TCP, HTTP API, MQTT (эмуляторы в `DeviceProtocolEmulator`).
- DAL (E47): драйверы `.fnp` (atol-kkt, shtrih-kkt, hikvision-face, zebra-scanner).

**Оговорки по тестам / эмуляция:**
- Репозиторий `.fnp` — константа в коде, не внешний registry.
- Ping устройств всегда возвращает `online`.
- Связка DAL ↔ legacy devices — не реализована (TODO: миграция).

## E16 — Аналитика и дашборд (ТЗ §4.19)

**Что важно помнить:**
- Дашборд: KPI (выручка, посещения, churn, LTV), графики, SSE-обновления.
- AI-аналитика: churn score, heatmap, рекомендации (E44).
- Тонкий клиент: вкладка «Аналитика» с dashboard + AI churn + risk-segments (E52).

**Оговорки по тестам / эмуляция:**
- Churn score — rule-based, не ML (E44).
- Heatmap — агрегация в Python, не SQL (может тормозить на больших объёмах).

## E17 — Уведомления (ТЗ §4.17, §15)

**Что важно помнить:**
- Каналы: Email, SMS, WebPush, Telegram, MAX.
- Дайджест: ежедневный отчёт (APScheduler), настраивается в `notification_settings`.
- Журнал: `notification_log` — все отправленные сообщения.

**Оговорки по тестам / эмуляция:**
- SMS — эмуляция (E29 phone-verify, E34 marketing); боевые: SMSRU, Twilio.
- WebPush — заглушка FCM (E24).
- Автонапоминания (E57) — ручная кнопка «Сгенерировать»; в проде — cron.

## E18 — Коммерция и White-label (ТЗ §4.2)

**Что важно помнить:**
- White-label: название клуба, логотип, primary/secondary цвета, favicon.
- Тенанты: `tenants` (multi-club), `commerce_settings`.
- Тонкий клиент: брендинг подтягивается из `/commerce/settings`.

**Оговорки по тестам / эмуляция:**
- Цвета валидируются regex HEX; кастомный цвет — через диалог (E52).
- Нет CDN для assets — файлы локальные.

## E19 — Экспорт данных (ТЗ §4.18, 152-ФЗ)

**Что важно помнить:**
- Форматы: xlsx, csv (BOM + `;`), json, xml.
- Асинхронные задачи: `POST /export/jobs` → JWT-ссылка на скачивание (24ч).
- All-my-data: ZIP со всеми сущностями (GDPR / 152-ФЗ).
- Анонимизация: `POST /clients/{id}/anonymize`.

**Оговорки по тестам / эмуляция:**
- Скачивание по `/download?token=` (не `/export/download` — был shadowing, исправлено).
- CSV-экспорт — BOM для Excel, разделитель `;`.

## E20 — Бухгалтерия (ТЗ §4.16, E32)

**Что важно помнить:**
- ПКО/РКО: `POST /accounting/pko`, `/accounting/rko`.
- Отчёты: ОСВ, прибыль-убыток, баланс, проводки.
- План счетов: 50 (Касса), 51 (Банк), 62 (Клиенты), 90.1 (Выручка), 91.2 (Расходы), 99 (Прибыль).
- Тонкий клиент: вкладка «Бухгалтерия» с ПКО/РКО/отчётами.

**Оговорки по тестам / эмуляция:**
- 1С-экспорт — mock (упрощённый XML, не CommerceML).
- Автопроводки — ручные триггеры (`/auto/from-sale`).

## E21 — Интеграция A&A (ТЗ §4.21)

**Что важно помнить:**
- Импорт CSV: `POST /aa/import-csv` (JSON-обёртка с полем `csv`).
- Автоопределение колонок: ФИО, Телефон, Email, Дата рождения, Пол, Категория, Статус, Фото(URL).
- Парсинг ФИО из одной колонки: `Иванов Иван Иванович` → last/first/middle.
- Нормализация enum: gender → MALE/FEMALE, category → ADULT/VIP/STAFF, status → ACTIVE/INACTIVE.
- Экспорт: JSON или CSV; журнал синхронизации: `/aa/sync-log`.
- Webhook: `POST /aa/webhook` (incoming от A&A).

**Оговорки по тестам / эмуляция:**
- Импорт НЕ создаёт абонементы/платежи — только клиенты.
- `updated_at` NOT NULL — исправлено в INSERT (NOW()).
- Тонкий клиент: вкладка «Интеграции» → подвкладка A&A (импорт, экспорт, журнал, webhook URL).



## Общее / безопасность
- `.env` попадал в git-историю — секреты (пароли БД, SECRET_KEY) считать скомпрометированными, перед продом ротировать.
- Face ID — только self-hosted (без FindFace/NtechLab/Face++): лицензии + 152-ФЗ.
- WebSocket/подключения — только 127.0.0.1 (IPv6 ::1 заблокирован на машине разработки).

## E22 Online Training
- E22.9/10: запись сессий логическая (метаданные в БД), реального медиасервера нет.
- E22.13: endpoint /online-sessions/reminders/run готов, нужен планировщик (apscheduler/cron).
- E22.14/15: ссылки Zoom/Google Meet генерируются фабрикой; боевые API — после добавления ключей.

## E23 Hardware
- E23.13–15: работа через DeviceProtocolEmulator (modbus_tcp/http_api/mqtt); боевые контроллеры — заменить эмулятор на драйверы.

## E24 Messenger
- E24.15: push — точка интеграции FCM (заглушка {"channel": "fcm"}).

## E25 Telegram Bot / MAX Bot
- Отправка сообщений идёт в боевой API только при настроенных токенах (TelegramSettings / MaxBotSettings в БД).
- /cron/subscription-expiry и /cron/booking-reminder — готовы к подключению к планировщику.

## E26 YooKassa
- Реальные ключи YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY в .env — и модуль переключится с эмуляции на боевой API (yookassa_service.py уже умеет ходить в api.yookassa.ru).
- Для международных платежей архитектура готова: поле payment_system в payments — добавить Stripe/CloudPayments = ещё один роутер рядом с /yookassa.
- Переключатель /yookassa/test/simulate — только для тестов, в проде отключить (или оставить — он под авторизацией).
- Подпись webhook: у боевой YooKassa проверка по IP-списку; наш HMAC (X-YooKassa-Signature) — дополнительная защита endpoint'а, в проде комбинировать оба подхода.
- E26.12/13: эмуляция сбоев через переключатель; реальные 503/504 от api.yookassa.ru обрабатываются тем же кодом через try/except в _api() сервиса.
- E26.9/10: рекуррент — реальный автоплатёж требует save_payment_method: true при первом платеже и списание по payment_method_id; логика списания готова, боевой вызов API — одна строчка при появлении ключей.



## E30 Setup Master
- Состояние мастера — таблица setup_wizard (БД); старый механизм на файлах (.setup_state, app/core/license_guard) сохранён для legacy-эндпоинтов. В проде унифицировать на БД.
- /setup/status и /setup/complete расширены полями setup_required/steps/current_step и setup_complete/redirect_to_dashboard — старые поля (is_complete и пр.) сохранены.
- Проверка лицензии в /complete принимает и license_guard (файл), и лицензию из БД (E28).
- Шаги devices/tariffs/club сохраняются как JSON в setup_wizard; в проде — запись в реальные таблицы equipment/tariffs/clubs.
- /setup/reset чистит setup_wizard и удаляет .setup_state.

## E29 Phone Verify
- `dev_code` в ответе /phone-verify/send — ТОЛЬКО для тестов; в проде убрать из ответа (код должен уходить только в SMS/мессенджер).
- Провайдеры smsru/twilio/whatsapp/telegram — эмуляция. Боевые интеграции: ключи SMSRU_API_KEY, TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN, WhatsApp Business API; отправка через telegram — по telegram_links (E25).
- /phone-verify/test/providers — тестовый переключатель сбоев, в проде отключить.
- Rate-limit (5 попыток/15 мин, resend 1/мин) — в БД/памяти; в проде при нескольких инстансах вынести в Redis.
- TTL кода 5 мин; верификация при регистрации: register сохраняет phone, /verify ставит users.phone_verified=true.

## E28 License
- License server — локальная эмуляция (POST /license/generate выдаёт ключи FITI-XXXXXXXX-CCCC с HMAC-контрольной суммой). В проде ключи выдаёт внешний вендор-сервер; HMAC-подпись лицензии стоит заменить на асимметричную (Ed25519): публичный ключ зашит в код, приватный у вендора.
- Лицензия живёт в существующей таблице licenses (модель face_id.License), добавлены колонки device_limit/grace_days/offline_days/last_check/plan. Legacy-эндпоинты /license/verify|limits|revoke|activations сохранены со старой заглушкой авторизации — в проде перевести на реальную.
- Устройства — таблица license_devices (license_ref текстовый, т.к. id лицензии integer).
- E28.13/14: офлайн-режим проверяется по last_check в БД; реальная «работа без интернета» должна дополнительно гасить защищённые запросы через middleware.
- Секрет подписи: LICENSE_SECRET в .env (дефолт test-only).


## E31 — Фискализация (АТОЛ / Штрих-М, ОФД)

- Драйверы ФР (`/fiscal/atol`, `/fiscal/shtrih`) — ЭМУЛЯЦИЯ: чек пишется в
  `fiscal_receipts` со сгенерированным 10-значным ФН/ФП, никакого реального
  соединения с ККТ нет. Боевое подключение — через
  `app/services/fiscal/universal_fiscal.py` (ДТО АТОЛ / драйвер Штрих-М).
- ОФД (в т.ч. Taxcom) — эмуляция: `ofd_status` всегда "delivered",
  `ofd_url` — заглушка. В проде нужна реальная отправка в ОФД и проверка
  статуса по чеку.
- `/fiscal/test/drivers` — ТОЛЬКО для тестов (переключает доступность
  драйверов в памяти процесса). В проде удалить или закрыть feature-флагом.
- Настройки ФР хранятся в `fiscal_settings` (одна строка, upsert);
  POST /settings — только admin.
- Смена — одна запись в `fiscal_shift` (is_open). Z-отчёт закрывает смену,
  X-отчёт требует открытой. close-shift идемпотентен (без 400).
- Фискализация НЕ требует открытой смены (в проде на реальном ФР — требует,
  драйвер сам вернёт ошибку).
- Повторная фискализация того же receipt_id -> 400 (идемпотентность по
  receipt_id) — в проде сохранить.
- Суммы в X/Z-отчётах — упрощённые (SUM(amount) по receipt_type='sale'),
  без разбивки по типам оплаты/налогам.


## E32 — Внутренняя бухгалтерия (проводки, отчёты, 1С-обмен)

- E32-блок ДОПИСАН в существующий app/api/v1/endpoints/accounting.py
  (там уже были /pko, /rko, /sale, /osv, /1c/* на InternalAccounting +
  OneCIntegration(mode="mock")). Параллельный модуль не создавался.
- Счета — условные строки: cash (Касса), bank (Банк), revenue (Выручка),
  receivables (Дебиторка), expense (Расходы), profit (Прибыль). В проде —
  привязка к плану счетов (50/51/62/90/91/99) и двойная запись по
  существующему InternalAccounting.
- accounting_entries.entry_date — VARCHAR(10) ISO-даты (избегаем проблем
  cast text->date через psycopg); сравнения периодов лексикографические.
- Экспорт /export/1c — упрощённый собственный XML (<entries><entry .../>),
  НЕ CommerceML/EnterpriseData. Для боевой 1С — формат обмена по
  конфигурации (уже есть OneCIntegration, сейчас mode="mock").
- /import/1c принимает тот же упрощённый XML; без дедупликации —
  повторный импорт того же файла создаст дубли проводок.
- Автопроводки /auto/from-sale и /auto/from-payment — ручные триггеры.
  В проде должны вызываться из событий продажи/платежа (webhook YooKassa
  E26 уже пишет платежи — связка пока не автоматическая).
- close-month идемпотентен по (year, month): повтор -> "Месяц уже закрыт".
  Проводки закрытия — только revenue->profit и profit->expense.
- Баланс счёта = SUM(дебет) - SUM(кредит) без сальдо на начало периода.


## E33 — Документы (шаблоны, подписание, PDF/DOCX, ЭП)

- Шаблоны сидятся в document_templates (code: subscription_contract,
  gdpr_consent, medical_certificate), плейсхолдеры {{client_name}},
  {{client_phone}}, {{client_email}}, {{birth_date}}, {{tariff}}, {{date}} —
  простая str.replace-подстановка, без движка шаблонов (Jinja2 не нужна,
  но в проде лучше формализовать).
- template_id при создании можно не передавать — резолвится по type.
  Если type неизвестен и template_id пуст -> 422 'template_id обязателен'.
- PDF генерируется ВРУЧНУЮ (минимальный PDF-1.4, Helvetica): кириллица
  заменяется на '?' (latin-1). Для прода — reportlab/weasyprint с
  русскими шрифтами.
- DOCX — минимальный валидный OOXML-пакет (zip: [Content_Types].xml,
  _rels/.rels, word/document.xml), кириллица ОК (UTF-8). Для прода —
  python-docx с полноценной вёрсткой.
- send-email и print — ЭМУЛЯЦИЯ (ничего не отправляется/не печатается).
  В проде: email через SMTP/SendGrid, печать через принт-сервис/CUPS.
- sign-ep — ЭМУЛЯЦИЯ CAdES: signature_valid всегда true при наличии
  certificate. В проде — КриптоПро/ГОСТ Р 34.10-2012, проверка цепочки
  сертификатов УЦ, формат CAdES-BES/T.
- Подписанный документ нельзя подписать повторно (400) — и для простой
  подписи, и для ЭП. Удаление документа — физическое (в проде, возможно,
  нужен soft-delete/архив для юрзначимых документов).


## E34 — Маркетинг (кампании, сегменты, рассылки, аналитика, ROI, A/B)

- E34-блок ВСТРОЕН в существующий app/api/v1/marketing.py: старые
  GET/POST /campaigns (через MarketingService + require_permission)
  заменены на raw-SQL реализацию с get_current_user. Остальные старые
  эндпоинты (/segments GET, /send-sms, /send-email, /campaigns/{id}/launch)
  не тронуты.
- Новые таблицы: marketing_campaigns, marketing_segments. Старые модели
  marketing_campaign/marketing_trigger (ORM) не используются E34-блоком —
  в проде унифицировать.
- Рассылки send-email/sms/push/telegram — ЭМУЛЯЦИЯ: sent = COUNT клиентов
  (или telegram_links), failed = 0, ничего реально не отправляется. В проде:
  очередь задач (Celery/ARQ) + реальные шлюзы, учёт отписок (152-ФЗ,
  38-ФЗ о рекламе), suppression-листы.
- Сегментация: критерии мапятся на колонки clients по information_schema
  (безопасно от SQL-инъекций по ключам), пустые criteria = все клиенты.
- Аналитика (open/click/conversion) — ЗАГЛУШКА с фиксированными числами.
  ROI = упрощённо revenue = budget x 3.2. В проде — реальные события
  открытий/кликов (пиксель/редиректы) и связь с продажами.
- A/B тест — эмуляция (winner по длине текста). В проде — случайное
  разделение сегмента и статистическая значимость.
- Mailchimp/SendGrid — эмуляция (сгенерированные id). В проде — реальные
  API-ключи в .env (НЕ коммитить, см. общий раздел про ротацию секретов).


## E35 — Терминал самообслуживания (Self-Service)

- E35-блок — отдельный роутер e35_router (prefix /self-service) в
  существующем app/api/v1/selfservice.py; старые ручки /selfservice/*
  (profile, subscriptions, visits) не тронуты.
- Face ID — ЭМУЛЯЦИЯ: photo хранится как строка в terminal_faces и
  матчится точным сравнением; 'blurry' в строке = лицо не распознано.
  В ПРОДЕ — ТОЛЬКО self-hosted распознавание (свой сервис, см. общий
  раздел: НЕ FindFace/NtechLab, НЕ Face++ cloud — лицензии и 152-ФЗ,
  биометрия = особая категория ПДн, нужно согласие клиента).
- /self-service/test/terminal — ТОЛЬКО для тестов (переключает
  _TERMINAL['online'] в памяти процесса). В проде удалить/закрыть.
- Регистрация создаёт реального клиента в clients (gender NOT NULL —
  хардкод 'male', в проде брать из анкеты), карту в terminal_cards,
  абонемент в subscriptions. card_number генерируется FIT-XXXXXXXX.
- Бронирование: слот = строка slot_datetime в self_service_bookings,
  конфликт = точное совпадение (service_id, slot_datetime) -> 409.
  В проде — интервальная проверка (duration_minutes услуги) и лимиты
  max_capacity.
- Баланс — из wallets (0.0, если кошелька нет). Заморозка: status
  active<->frozen в subscriptions (frozen_at, freeze_reason).
- QR-код — просто строка FITQR-... (без PNG). В проде — генерация
  изображения (qrcode lib) и ротация/подпись токена.
- pay-terminal — эмуляция эквайринга (slip_printed=true). В проде —
  драйвер банковского терминала (Сбер/Тинькофф SDK).

## E36 — Рекуррентные платежи (ТЗ §4.7)

Что важно помнить про модуль:
- Таблицы: recurring_schedules (расписания: интервал day/week/month, next_charge_at VARCHAR(19), status active/paused/cancelled/failed, retry_count/max_retries), recurring_charges (история попыток списаний).
- POST /api/v1/recurring/run — синхронный прогон должников (status='active' AND next_charge_at<=now). В проде должен вызываться планировщиком (cron/Celery beat/APScheduler), а не вручную.
- Ретраи: экспоненциальная пауза 2^n часов; при retry_count >= max_retries расписание -> status 'failed' (last_error "Превышено число попыток списания").
- month = 30 дней (упрощение, не календарный месяц). next_charge_at после успеха считается от предыдущей даты списания (catch-up: при долгом простое возможны подряд идущие списания — так задумано, чтобы догнать пропущенные периоды).

Оговорки по тестам / что эмулировано:
- Само списание эмулируется: реальный вызов YooKassa API (payment с сохранённой картой) НЕ выполняется; payment_id = "yk-<hex>" локальный. Для прода — подключить yookassa_service.create_payment(card_id, amount).
- /test/fail-next и /test/clear — ТОЛЬКО для тестов (in-memory флаг, не переживает рестарт).
- Уведомления клиенту о неудачном списании не отправляются (TODO: интеграция с notifications/E13 MAX Bot).
- Даты хранятся как VARCHAR(19) "%Y-%m-%d %H:%M:%S" (лексикографическое сравнение).
- Авторизация: чтение — любой аутентифицированный, мутации и /run — admin.

## E37 — Реферальная программа (ТЗ §4.9)

Что важно помнить:
- Таблицы: referral_codes (client_id UNIQUE, code "REF-XXXXXXXX"), referrals (referrer/referred, status registered/rewarded/rejected), referral_rewards (kind referrer_bonus/referred_bonus, status accrued/paid).
- POST /codes идемпотентен: повтор для того же client_id -> 200 existing=true, тот же код.
- Антифрод: самоприглашение -> 400; повторная регистрация referred -> 409.
- Двусторонние бонусы: реферер 500р, приглашённый 300р (дефолт, переопределяется в /reward).
- /payout переводит accrued -> paid пакетно.

Оговорки по тестам / эмуляция:
- Бонусы — учётные записи в БД, реальное начисление на wallet клиента НЕ выполняется (TODO: интеграция с wallets/loyalty).
- Регистрация приглашения НЕ проверяет существование referred_client_id в clients (приглашённый может ещё не быть клиентом клуба — атрибуция по ссылке).
- referred_client_id в тестах — сгенерированный UUID, не реальный клиент.
- Авторизация: коды/регистрация/баланс — любой аутентифицированный; reward/payout/stats/delete — admin.

## E38 — Корпоративные продажи (ТЗ §4.12)

Что важно помнить:
- Таблицы: corporate_companies (ИНН UNIQUE 10/12 цифр, discount_percent), corporate_contracts (number "DOG-XXXXXXXX", статусы draft/active/terminated, seats — лимит мест), corporate_members (soft-remove status removed), corporate_invoices (issued/paid).
- Лимит мест: при добавлении сотрудника COUNT(active members) >= seats -> 409 "Лимит мест исчерпан" (проверяется ДО существования клиента).
- Расторжение договора автоматически снимает всех сотрудников (status removed).
- Счёт по умолчанию = цене договора; период по умолчанию = текущий YYYY-MM.

Оговорки по тестам / эмуляция:
- Оплата счёта эмулируется (статус issued->paid), интеграции с банком/1С нет (для 1С см. E32 export).
- Сотрудникам НЕ создаются абонементы автоматически (TODO: связка с subscriptions по tariff_id договора).
- ИНН проверяется только по формату (10/12 цифр), контрольная сумма не считается.
- Авторизация: чтение — любой аутентифицированный, мутации — admin.

## E39 — Сезонные кампании (ТЗ §4.14)

Что важно помнить:
- Таблицы: seasonal_campaigns (season winter/spring/summer/autumn/new_year/custom, promo_code UNIQUE "SALE-XXXXXX", статусы draft/active/finished, auto_activate), seasonal_promo_uses (одно применение на клиента на кампанию -> 409).
- Валидация промокода: активность + окно дат (start_date/end_date VARCHAR(10), лексикографика); скидка = amount * discount_percent / 100.
- POST /auto-activate — пакетный перевод по календарю: draft+auto_activate+start_date<=today -> active; active+end_date<today -> finished. В проде — по планировщику (как /recurring/run).

Оговорки по тестам / эмуляция:
- Применение промокода НЕ создаёт платёж/заказ — только фиксирует использование (TODO: связка с payments/subscriptions при покупке).
- Скидка только процентная, фиксированной суммы нет.
- Промокод одноразовый на клиента, лимита активаций нет (TODO: max_uses).
- Авторизация: чтение/валидация — любой аутентифицированный; CRUD/activate/finish/auto-activate — admin.

## E40 — Нишевые шаблоны (ТЗ §4.11)

Что важно помнить:
- Таблицы: niche_templates (code UNIQUE, config JSON TEXT, is_builtin), niche_template_applies (история применений).
- 6 встроенных шаблонов: fitness, yoga, martial_arts, dance, swimming, crossfit (seed в setup_e40.py, идемпотентен).
- Встроенные шаблоны immutable: PUT/DELETE -> 400. Кастомные — полный CRUD + clone.
- Применение создаёт записи в tariffs и services клуба через _insert с фильтрацией по information_schema.

Оговорки по тестам / особенности:
- ОБЯЗАТЕЛЬНЫЕ поля tariffs: code (генерим "NICH-XXXXXXXX"), currency='RUB', is_unlimited=false, created_at/updated_at (datetime-объекты). У services обязательна category (= имя ниши), duration_minutes=60 по умолчанию.
- Тарифы/услуги из шаблона дублируются при повторном apply (дедупликации нет — TODO: проверка по имени+club_id).
- club_id при apply не валидируется по таблице клубов (свободная строка).
- Авторизация: чтение — любой аутентифицированный; create/update/delete/apply/clone — admin.

## E41 — Online Booking Widget (ТЗ §4.8)

Что важно помнить:
- Таблицы: widget_settings (club_id UNIQUE, is_enabled, title/primary_color/logo_url, allowed_services JSON, require_phone), widget_bookings (statuses new/confirmed/cancelled).
- Публичные эндпоинты БЕЗ авторизации: /public/{club_id}/config|services|slots|book, /public/{club_id}/booking/{id}, cancel по телефону, /embed/{club_id}. Админские — /settings, /bookings, confirm/cancel (admin).
- Слоты генерируются на лету: почасовые 09:00–20:00, занятые = widget_bookings (status<>'cancelled') по service_id+slot_datetime.
- Отмена гостем — по совпадению телефона (403 "Телефон не совпадает").

Оговорки по тестам / эмуляция:
- Слоты НЕ связаны с реальным расписанием услуг/тренеров (фиксированные часы 09–20; TODO: интеграция с schedule/service_bookings).
- Запись гостя НЕ создаёт клиента в CRM (TODO: авто-создание лида по телефону).
- Уведомления о записи/подтверждении не отправляются (TODO: notifications).
- widget.js на cdn.fitintel.pro — заглушка-URL, сам JS-бандл виджета не реализован.
- Телефон валидируется regex ^\+?\d[\d\s\-()]{9,}$.

## E42 — Documents: массогенерация + events/signatures/relations (ТЗ §13)

Что важно помнить:
- Новый файл app/api/v1/documents_bulk.py с тем же prefix /documents (роутеры сливаются). ВАЖНО: include documents_bulk_router стоит ВЫШЕ documents (E33) в main.py — иначе GET /{document_id} из E33 перехватывает /mass-jobs (была ошибка E42.4).
- Таблицы: document_events (created/generated/viewed/signed...), document_signatures (signer_role UNIQUE в рамках документа, is_valid), document_relations (related_type: subscription/payment/contract/visit), document_jobs (total/done/failed, document_ids JSON, errors JSON).
- Массогенерация синхронная: job сразу status=done; несуществующие клиенты идут в failed+errors, не роняют задачу.
- Подписи дедуплицируются по signer_role (400 "Подпись этой стороны уже есть"); каждая подпись пишет событие signed в журнал.

Оговорки по тестам / эмуляция:
- Рендер шаблона — простая подстановка {{client_name}}/{{client_phone}}/{{client_email}}/{{date}}; PDF/DOCX-файлы при массогенерации НЕ создаются (content только текст; генерацию файлов см. E33 /download).
- ip_address подписи хардкод 127.0.0.1 (в проде — из request.client).
- Это НЕ криптографическая ЭП (для УКЭП см. E33 /sign-ep, эмуляция CAdES).
- Авторизация: mass-generate/delete — admin; events/signatures/relations чтение и добавление — любой аутентифицированный.

## E43 — Feature Flags advanced (ТЗ §4.27, UC-2)

Что важно помнить:
- Новый файл app/api/v1/feature_flags_adv.py (prefix /feature-flags), include в main.py стоит ВЫШЕ базового feature_flags_router — все advanced-пути двухсегментные (/rollout/{key}, /evaluate/{key}, /license-bind/{key}, /stats/{key}), конфликтов с базовым CRUD нет.
- Таблицы: ff_rollouts (strategy percentage/canary, percent, canary_users JSON), ff_license_binds (license_feature, required), ff_evaluations (история оценок), ff_license_features (эмуляция фич лицензии: core/crm/payments/analytics_basic).
- Оценка: license-bind (deny при отсутствии фичи, reason license_denied) -> rollout (canary по списку / percentage по бакету MD5(user_id:flag_key)%100) -> default (is_active + default_value JSON).
- Бакет детерминированный — один и тот же user всегда получает одинаковый результат при том же percent.
- WebSocket /api/v1/feature-flags/stream: broadcast при изменении rollout; POST /test/broadcast — test-only.

Оговорки по тестам / эмуляция:
- Проверка лицензии эмулируется таблицей ff_license_features (TODO: заменить на вызов сервиса лицензий E28).
- Redis-кэш оценки (требование ≤10мс из ТЗ) НЕ реализован — чтение из PostgreSQL напрямую.
- WS /stream тестами не покрыт (нет ws-клиента в тестах) — проверен только broadcast-эндпоинт (sent=0 без подключений).
- evaluate требует авторизации; для публичных клиентских SDK нужен отдельный токен/scope.

## E44 — AI Analytics (ТЗ §4.20)

Что важно помнить:
- Новый файл app/api/v1/analytics_ai.py, prefix /analytics, пути под /ai/* — конфликтов с базовой аналитикой нет.
- Churn score (0-100) rule-based: >30 дней без визитов +60, >14 +40, >7 +15; 0 визитов за 30д +30; <2 визитов +15; абонемент <=14 дней +10. Уровни: low <30, medium 30-59, high >=60.
- Рекомендации rule-based по факторам: retention/winback/motivation/renewal/upsell/cross_sell.
- Heatmap: Python-агрегация visits по weekday/hour (адаптивно к типу колонки даты: timestamptz или VARCHAR).
- Колонка даты visits определяется адаптивно: visited_at/visit_date/check_in_at/created_at/start_time.

Оговорки по тестам / эмуляция:
- Это НЕ ML-модель — rule-based эвристика (model "rules-v1"). Для прода: ML (scikit-learn/XGBoost) с обучением на исторических оттоках, фичи уже считаются в _churn_score.
- /ai/recalc — заглушка (считает COUNT клиентов), т.к. расчёт on-the-fly.
- Churn-список и сегменты ограничены 500 активными клиентами (LIMIT 500).
- Heatmap читает ВСЕ visits и фильтрует в Python — на больших объёмах нужна SQL-агрегация.
- Рекомендации не отправляются (TODO: связка с marketing E34 / notifications).

## E45 — Video Analytics advanced (ТЗ E12)

Что важно помнить:
- Новый файл app/api/v1/video_ai.py, prefix /video-ai. Дополняет базовые video_alerts.py (7 роутов) и face_id.py (9 роутов).
- Таблицы: video_triggers (event_type intrusion/loitering/crowd/fall/tailgating, threshold 0-1, learn_samples), video_trigger_events (statuses new/confirmed/false_alarm), video_cameras (discovered_via onvif/manual, ip UNIQUE-поведение через проверку 409).
- Feedback-loop: false-alarm автоматически дообучает триггер (learn_samples+1, threshold +0.005, cap 0.99).
- Событие не создаётся, если confidence < threshold триггера (400) или триггер неактивен (400).

Оговорки по тестам / эмуляция:
- ONVIF discovery ЭМУЛИРОВАН: фиксированный список 192.168.1.64/.65 (в проде — WS-Discovery UDP probe на порт 3702 + парсинг XAddrs).
- Edge-инференс не реализован: нет реального видеопотока/детекции (события создаются через API-эмуляцию POST /events).
- Snapshot URL — заглушка /snapshots/{id}.jpg (файлы не сохраняются).
- Обучение триггеров — численная эмуляция (threshold растёт от samples), не ML.
- Авторизация: события/чтение — любой аутентифицированный; triggers/cameras/discover — admin.

## E46 — MAX Bot FSM (ТЗ §15.3.5, E13)

Что важно помнить:
- Новый файл app/api/v1/max_bot_fsm.py, prefix /max-bot/fsm — дополняет max_bot.py (API: setup/webhook/cron), не конфликтует.
- FSM: start -> main_menu -> booking_service -> booking_date -> booking_confirm -> main_menu. Состояние и контекст в bot_sessions (user_id UNIQUE, context JSON).
- Из состояния start ЛЮБОЕ сообщение = приветствие -> main_menu (не обрабатываются команды сценария — так задумано).
- Валидация §15.3.5: услуга строго из клавиатуры; дата ДД.ММ.ГГГГ / Сегодня / Завтра, не в прошлом; ошибки валидации возвращают 200 с reply-подсказкой и той же клавиатурой (не HTTP 4xx — это чат-бот).
- Подтверждённая запись пишется в bot_bookings (status new).

Оговорки по тестам / эмуляция:
- Это FSM-ядро БЕЗ транспорта: сообщения приходят через POST /message (в проде вызывается из webhook max_bot.py).
- "Мой абонемент"/"Баланс" — заглушки, не читают реальные subscriptions/wallets (TODO: по user_id -> telegram_links -> client).
- Клавиатуры — массивы строк в JSON (структура под MAX API, не подтверждена боевым API MAX).
- Сценариев пока один (booking); сценарий привязки телефона описан, но не включён в FSM.
- Авторизация: все эндпоинты — аутентифицированный пользователь (в проде /message вызывается сервисом webhook, нужен service-token).

## E46 — MAX Bot FSM (ТЗ §15.3.5, E13)

Что важно помнить:
- Новый файл app/api/v1/max_bot_fsm.py, prefix /max-bot/fsm — дополняет max_bot.py (API: setup/webhook/cron), не конфликтует.
- FSM: start -> main_menu -> booking_service -> booking_date -> booking_confirm -> main_menu. Состояние и контекст в bot_sessions (user_id UNIQUE, context JSON).
- Из состояния start ЛЮБОЕ сообщение = приветствие -> main_menu (не обрабатываются команды сценария — так задумано).
- Валидация §15.3.5: услуга строго из клавиатуры; дата ДД.ММ.ГГГГ / Сегодня / Завтра, не в прошлом; ошибки валидации возвращают 200 с reply-подсказкой и той же клавиатурой (не HTTP 4xx — это чат-бот).
- Подтверждённая запись пишется в bot_bookings (status new).

Оговорки по тестам / эмуляция:
- Это FSM-ядро БЕЗ транспорта: сообщения приходят через POST /message (в проде вызывается из webhook max_bot.py).
- "Мой абонемент"/"Баланс" — заглушки, не читают реальные subscriptions/wallets (TODO: по user_id -> telegram_links -> client).
- Клавиатуры — массивы строк в JSON (структура под MAX API, не подтверждена боевым API MAX).
- Сценариев пока один (booking); сценарий привязки телефона описан, но не включён в FSM.
- Авторизация: все эндпоинты — аутентифицированный пользователь (в проде /message вызывается сервисом webhook, нужен service-token).

## E47 — DAL, Device Abstraction Layer (ТЗ §4.26, E15)

Что важно помнить:
- Новый файл app/api/v1/dal.py, prefix /dal. Таблицы: dal_drivers (package_name UNIQUE, status installed/enabled/disabled/error, manifest JSON), dal_devices (connection_string, last_seen), dal_events (ping/command журнал).
- Репозиторий .fnp-пакетов — константа REPOSITORY (5 пакетов: atol-kkt, shtrih-kkt, mercury-scale, hikvision-face, zebra-scanner). Install копирует manifest из репозитория; upgrade сверяет с latest_version.
- Автообнаружение устройств: берёт discovery-список из manifest драйвера, дедупликация по (driver_id, connection_string). Только для status=enabled.
- Каскад: удаление драйвера удаляет его устройства и их события.

Оговорки по тестам / эмуляция:
- Репозиторий и discovery ЭМУЛИРОВАНЫ константами (в проде: внешний registry .fnp + реальные probe-запросы драйверов).
- .fnp-пакет не распаковывается и не исполняется (нет sandbox-загрузчика driver.py); execute() — эмуляция echo.
- ping всегда возвращает online (эмуляция).
- Версии сравниваются строкой (нет semver-разбора).
- Авторизация: чтение — любой; install/enable/disable/upgrade/delete/discover/add — admin; ping/command — любой аутентифицированный.
- Связка с Device Manager: devices.py/equipment.py остаются на своих таблицах (TODO: миграция их устройств в dal_devices).

## E48 — Регламентированная отчётность (ТЗ §16.2)

Что важно помнить:
- Новый файл app/api/v1/reporting.py, prefix /reporting. Таблица payroll_records (employee_name, inn, period YYYY-MM, income, deductions).
- 6-НДФЛ: НДФЛ = max(income - deductions, 0) * 13%, группировка по сотруднику за квартал. РСВ: единый тариф 30% (ОПС 22 + ОМС 5.1 + ВНиМ 2.9) от начислений.
- УСН считается из accounting_entries (E32): доходы = SUM(credit revenue), расходы = SUM(debit expense); оба варианта 6%/15% + рекомендация.
- /calendar — фиксированные дедлайны ФНС; /summary — готовность данных за год.

Оговорки по тестам / эмуляция:
- XML — УПРОЩЁННЫЙ, не официальный XSD-формат ФНС (для сдачи нужен генератор по схемам ФНС + выгрузка в Контур/СБИС).
- Ставка НДФЛ 13% фиксированная (прогрессивная шкала 15/18/20/22% не реализована).
- РСВ без разбивки по подразделам/превышению базы.
- Payroll — ручной ввод начислений; интеграции с табелем/расчётом зарплаты нет.
- Авторизация: чтение — любой аутентифицированный; payroll create/delete — admin.

## E50 — HA и резервное копирование (ТЗ §9, E10)

Что важно помнить:
- Новый файл app/api/v1/ops.py, prefix /ops. Бэкапы пишутся в ./backups/ (backup_YYYYMMDD_HHMMSS.sql).
- /backup/run: pg_dump если доступен в PATH, иначе каталог-дамп (список таблиц + row counts, помечен mode="catalog").
- Имя файла санитизируется (os.path.basename) — path traversal -> 400.
- Боевые скрипты: deploy/backup/backup.ps1 (pg_dump + ротация 14 дней, env FITINTEL_DB_PASSWORD), deploy/backup/restore.ps1.
- /replication честно отвечает single-node.

Оговорки по тестам / эмуляция:
- Restore через API — ЭМУЛЯЦИЯ (не выполняет psql); боевое восстановление — только через deploy/backup/restore.ps1.
- pg_dump на dev-машине может отсутствовать -> mode="catalog" (не полноценный дамп! только каталог).
- HA/репликация PostgreSQL НЕ настроена (single-node): для прода — Patroni/streaming replication + pgbouncer (см. deploy/).
- Ротация бэкапов в API не реализована — только в backup.ps1 (14 дней).
- Бэкап не включает Redis/файлы загрузок — только PostgreSQL.
- Авторизация: run/restore/delete — admin; list/health/replication — любой аутентифицированный.

## E51 — UI-Config (экраны тонкого клиента по ролям)

**Что сделано:** реестр из 17 экранов тонкого клиента (ui_screens), матрица «роль → экраны» (ui_role_screens, 5 ролей × все экраны), дефолтные профили superadmin/admin/manager/trainer/reception. API: GET /ui-config/screens, POST /screens (201/409), GET /roles (матрица), GET+PUT /roles/{role}/screens, POST /roles/{role}/reset, GET /my (тонкий клиент строит меню при входе). Алиасы ролей: administrator→admin, super_admin→superadmin и др. Защита от самоблокировки: нельзя скрыть ui_config у superadmin (400). Права: запись — superadmin/admin, чтение /my — любой авторизованный.

**Продакшен-оговорки:**
- Роль пользователя определяется из атрибута user.role/role_name (строка или enum) — при смене модели пользователей проверить маппинг.
- Новые экраны после POST /screens видны только superadmin — остальным ролям включаются вручную через PUT.
- Тонкий клиент (fitintel-desktop) пока не читает /ui-config/my — вкладки захардкожены; для полного замыкания UX добавить в main_window построение меню из /my.
- Мастер установки (E30) уже покрывает шаги license + devices (WIZARD_STEPS: database, license, admin, club, devices, tariffs, complete); устройства также через DAL (E47) — доработка не потребовалась.

## E52 — Тонкий клиент: прокачка (часть 1)

**Что сделано:** фикс логина (JSON /auth/login вместо form /auth/token); нормализация списков в api/client.py (_as_list: items/entries/users/...); visits_tab переписан — вместо UUID ФИО+телефон клиента (join по client_id), цветной статус, поиск; новые вкладки: Аналитика (dashboard + AI churn + risk-segments), Платежи (accounting entries), Пользователи, Устройства (DAL), Экраны ролей (редактор матрицы E51); main_window строит вкладки из GET /ui-config/my по роли с fallback на полный набор; авто-ремонт битых строк (\n в литералах) в 4 файлах клиента.

**Фикс данных БД (важно для прода!):** GET /clients/ падал с 500 — legacy-значения не совпадали с enum схемы. Мигрировано: gender МУЖСКОЙ/male→MALE; client_category ОБЫЧНАЯ/REGULAR/terminal→ADULT/STAFF; status→UPPER; NULL email→noemail-{id}@fitintel.local. **Рекомендация:** ослабить response-схемы (Optional/str) или добавить валидаторы на входе, чтобы legacy-данные не роняли список.

## E55 — Платежи / Face ID (тонкий клиент)
- Отдельного endpoint «отмена платежа» в API нет: кнопка «Отмена» = POST /payments/{id}/refund
  полной суммы с reason="Отмена платежа". Для прода: завести статус CANCELLED на бэкенде,
  чтобы отмена не смешивалась с возвратами в отчётах.
- /face-id/verify принимает {"photo": base64} (не face_encoding). Симуляция шлёт тестовое
  фото 1x1; в проде фото идёт с камеры терминала, anti-spoofing через /face-id/anti-spoofing.
- Экспорт платежей: POST /reports/payments/export (format=csv) — проверить формат ответа
  на реальных данных (файл или JSON со ссылкой).

## E56 — Помощь / MAX / Интеграции
- Меню «Помощь» в клиенте: инструкция по экрану (F1), чат с клиентами (MAX), поддержка разработчика (MAX).
  MAX_SUPPORT_URL в help_dialog.py — заменить на реальный чат поддержки.
- MAX Bot API: база https://platform-api.max.ru (Long Polling — platform-api2.max.ru),
  токен ТОЛЬКО в заголовке Authorization (query не поддерживается). Бота может создать
  только верифицированное юрлицо РФ («MAX для бизнеса»). Long Polling — только для dev,
  для прода настроить Webhook (POST /subscriptions, HTTPS с доверенным сертификатом).
- integration_settings: ключи хранятся в БД открытым текстом — перед продом шифровать (Fernet/Vault).
- Эндпоинты /integrations-config и /messenger пока без проверки роли — добавить Depends(get_current_user) + RBAC.

## E56 — Помощь / MAX / Интеграции
- Меню «Помощь» в клиенте: инструкция по экрану (F1), чат с клиентами (MAX), поддержка разработчика (MAX).
  MAX_SUPPORT_URL в help_dialog.py — заменить на реальный чат поддержки.
- MAX Bot API: база https://platform-api.max.ru (Long Polling — platform-api2.max.ru),
  токен ТОЛЬКО в заголовке Authorization (query не поддерживается). Бота может создать
  только верифицированное юрлицо РФ («MAX для бизнеса»). Long Polling — только для dev,
  для прода настроить Webhook (POST /subscriptions, HTTPS с доверенным сертификатом).
- integration_settings: ключи хранятся в БД открытым текстом — перед продом шифровать (Fernet/Vault).
- Эндпоинты /integrations-config и /messenger пока без проверки роли — добавить Depends(get_current_user) + RBAC.

## E57 — MAX: рассылки и напоминания
- Бот MAX пишет первым ТОЛЬКО пользователям, которые запустили бота — отсюда ручная
  привязка client_id ↔ max_user_id (подвкладка «Привязки»). Позже: авто-привязка по
  телефону при первом сообщении клиента.
- Напоминания генерируются кнопкой «Сгенерировать» — для прода повесить на планировщик
  (cron/планировщик Windows) вызов POST /messenger/reminders/run раз в день.
- Рассылка отправляется сразу через /messages (user_id); неотправленное висит в журнале
  со статусом no_binding/failed — «Отправить ожидающие» повторяет попытку.
- Автонапоминания читают subscriptions/visits «вглубь» через try/except — если схема
  колонок отличается, в ответе run придёт notes с текстом ошибки.

## E58 — Экран «Оповещения» (настройки отправки)
- Настройки хранятся в БД (notification_settings, одна строка JSON) — редактируются
  из клиента: канал MAX, время отправки, пороги (дни до истечения / дни неактивности),
  шаблоны с переменными {days} {date}.
- Новые типы оповещений добавляются: ключ в DEFAULT_SETTINGS (backend messenger.py) +
  поле на форме notifications_tab.py.
- Поле send_time пока справочное — реальную ежедневную отправку на проде должен делать
  планировщик (cron/Task Scheduler → POST /messenger/reminders/run в send_time).
- День рождения: правило-заглушка (нужна дата рождения клиента из БД — проверить колонку).
