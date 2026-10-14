# FitIntel Pro — Модуль «Мини-приложение MAX» и модуль «ЮKassa»

Версия документа: 2026-10-14. Актуальна для main-ветки репозитория.

---

# ЧАСТЬ 1. МИНИ-ПРИЛОЖЕНИЕ MAX

## 1.1. Назначение

Мини-приложение — клиентский кабинет клуба внутри мессенджера MAX. Клиент входит
**без пароля** (по подписи MAX), пополняет кошелёк, записывается на занятия,
видит расписание, новости и бонусы. Приложение — одностраничный HTML/JS
(`static/miniapp/index.html`) + набор API-эндпоинтов (`/api/v1/miniapp/*`,
`/api/v1/max-bridge/*`).

## 1.2. Пользовательская документация (для клиента)

### Вход и регистрация (MAX Bridge)

| Ситуация | Что происходит |
|---|---|
| Клиент открывает приложение по ссылке/QR бота, аккаунт есть | Сразу личный кабинет, **без пароля**. Вход подтверждён криптоподписью MAX (initData) |
| Клиент открывает приложение, аккаунта нет | Форма регистрации: ФИО (подставлено из профиля MAX), год рождения, пароль (мин. 8 симв.). Телефон НЕ вводится — подтверждается нативно кнопкой «Подтвердить телефон и зарегистрироваться» (запрос MAX «Поделиться номером?») |
| Вход с чужого устройства вне MAX | Телефон/e-mail + пароль (стандартный вход) |

Условие регистрации: карточка клиента заведена на ресепшене (по телефону).
Привязка MAX к карточке происходит автоматически.

### Экраны приложения

- **Главная** — лента «Новости клуба» (последние 3), наши тренеры, быстрые плитки.
- **Услуги** — каталог + кнопка **«Записаться на занятие»**:
  1. выбор тренера → 2. выбор занятия → 3. дата (дни из расписания услуги,
  группировка по месяцам) → 4. свободное время («мест: N») → подтверждение →
  «Запись создана». Запись видна в «Расписании» и в десктопе («Расписание → Записи»).
- **Расписание** — записи клиента.
- **Меню → Баланс • Бонусы** — виджет кошелька + кнопка **«+ Пополнить баланс»**
  (сумма → оплата → зачисление, см. Часть 2).
- **Меню → Профиль** — ФИО, дата рождения, контакты; кнопка **«Изменить данные»**.
- **Меню → Мой QR** — пропуск на турникет.

### Автоматические уведомления в MAX

- 🔔 **Напоминание о занятии** — за 3 часа до начала (параметр
  `BOOKING_REMIND_HOURS`), не чаще одного раза на запись.
- 🎁 **Бонусы за посещение** — при проходе в клуб (турникет/«Впустить»),
  по правилам из вкладки «Бонусы», не чаще раза в 12 ч (параметр
  `BONUS_VISIT_COOLDOWN_HOURS`).
- 📣 **Новости/акции** — при публикации из десктопа («MAX сообщения → Новости»):
  авторассылка всем привязанным клиентам + лента на Главной.

## 1.3. Техническая документация

### Архитектура

```
MAX (клиент) ──HTTPS──► nginx (fixintel.ru) ──► FastAPI (deploy-api-1)
                                    │
static/miniapp/index.html ◄─────────┘  (bind-mount, без пересборки)
API: app/api/v1/miniapp_config.py  (роутер /miniapp/* и /max-bridge/*)
     static/miniapp/index.html     (UI, токен в localStorage «fit_token»)
```

### MAX Bridge — вход без пароля

**`POST /api/v1/max-bridge/auth`** — body `{initData}`.
Проверка подписи initData (как у Telegram WebApp, но ключ MAX):
1. разобрать `k=v` пары, вынуть `hash`;
2. data-check-string = `"\n".join(f"{k}={unquote(v)}" for k in sorted)`;
3. secret = `HMAC_SHA256(key="WebAppData", msg=bot_token)`;
4. `hash == HMAC_SHA256(key=secret, msg=data-check-string)` (compare_digest);
5. свежесть: `|now - auth_date| <= 3600` сек.

Далее: ищем привязку `max_bot_bindings.max_user_id → clients → users`.
Найден → выпускаем JWT (7 дней). Не найден → `{registered: false, first_name,
last_name}` — клиент уходит на регистрацию.

**`POST /api/v1/max-bridge/register`** — body `{initData, full_name, birth_year,
password, phone, contact_hash, contact_auth_date}`.
Подтверждение телефона: `contact_hash == HMAC_SHA256(key=bot_token, msg=
"authDate={contact_auth_date}\nphone={phone_digits}\nuserId={max_user_id}")`.
Далее: поиск карточки клиента по последним 10 цифрам телефона → создание
пользователя (логин = 10 цифр) → роль `client` → привязка `clients.user_id` и
`max_bot_bindings` → JWT. Ошибки: 404 «карточка не найдена», 409 «аккаунт уже
существует».

### Эндпоинты /miniapp/* (все — Bearer JWT)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/miniapp/me` | Учётка + карточка (ФИО, birth_date, контакты) |
| POST | `/miniapp/me` | Правка ФИО/года/e-mail (users + clients) |
| GET | `/miniapp/wallet` | `{balance, bonuses}` — wallets.balance + gamification_levels.current_xp |
| GET | `/miniapp/wallet/config` | `{provider, min, bonus_percent}` |
| POST | `/miniapp/wallet/topup` | Пополнение (см. Часть 2) |
| GET | `/miniapp/booking/catalog` | Тренеры + услуги с расписанием (JSONB) |
| GET | `/miniapp/booking/slots?service_id&day` | Свободные слоты (ёмкость − занятые) |
| POST | `/miniapp/booking` | Создание записи (антипереполнение, 409 если мест нет) |
| GET | `/miniapp/booking/my` | Мои записи |
| POST | `/miniapp/news` | Публикация новости + рассылка (право админа) |
| GET | `/miniapp/news` | Лента (последние 10, таблица club_posts) |

### Права

Роли `client` и `admin` имеют право `wallet.read` (выдано GRANT'ом).
`/miniapp/wallet` отдаёт данные **только текущего** пользователя (привязка через
`clients.user_id`). Эндпоинты каталога/слотов — без авторизации (публичные данные).

### Уведомления (фоновые задачи)

- `w6_booking_remind` — apscheduler, каждые 20 мин: записи `BOOKED/CONFIRMED`
  в окне «сейчас + BOOKING_REMIND_HOURS ± 20 мин», `reminded_at IS NULL` →
  отправка → пометка `service_bookings.reminded_at`.
- Отправка — `app/integrations/max/service.py`: `POST https://platform-api.max.ru/messages?user_id={id}`,
  заголовок `Authorization: {bot_token}` (токен приоритетно из `max_bot_settings`,
  fallback env `MAX_BOT_TOKEN`). Телефон → `max_user_id` резолвится через
  `max_bot_bindings`. **Важно:** домен `platform-api2.max.ru` НЕ использовать —
  его цепочка TLS на УЦ Минцифры отсутствует в стандартных хранилищах.

### Правила бонусов (движок)

Таблица `bonus_rules` (категория × событие × fix/percent × значение × active).
`award_bonus(db, client_id, event, amount)`: выбирает правила по категории клиента
(`clients.client_category`, ALL — для всех, частные важнее), суммирует начисление,
зачисляет в `gamification_levels.current_xp` (`_add_xp`, создаёт строку при
отсутствии). События: `topup` (пополнение), `visit` (посещение), `purchase`,
`review`, `subscription`. CRUD: `/bonus-rules` GET/POST/DELETE. UI: десктоп
«Параметры клуба → Бонусы».

### Параметры конфигурации (club_params / «Временные параметры»)

| Ключ | По умолч. | Назначение |
|---|---|---|
| `WALLET_PAY_PROVIDER` | test | test / yookassa / sbp |
| `WALLET_TOPUP_MIN` | 100 | Мин. сумма пополнения, ₽ |
| `WALLET_BONUS_PERCENT` | 5 | Бонусы от пополнения, % (если нет правила topup) |
| `BONUS_VISIT_COOLDOWN_HOURS` | 12 | Пауза между бонусами за посещение, ч |
| `BOOKING_REMIND_HOURS` | 3 | За сколько часов напоминать о занятии |
| `YK_SHOP_ID`, `YK_SECRET_KEY` | — | Ключи ЮKassa (Часть 2) |

### Настройка онлайн-записи (для оператора клуба)

Запись в приложении работает, если у услуги заполнено онлайн-расписание —
поле `services.schedule` (JSONB). Формат:

```json
{
  "days": [0, 1, 2, 3, 4, 5, 6],
  "time_slots": [
    {"time": "10:00", "capacity": 8},
    {"time": "12:00", "capacity": 6},
    {"time": "18:00", "capacity": 10}
  ]
}
```

- `days` — дни недели, **0 = понедельник … 6 = воскресенье** (как Python);
- `time_slots` — время начала + ёмкость (мест на слот). Занятость считается по
  записям `service_bookings` со статусами BOOKED/CONFIRMED/PAID;
- услуга без `time_slots` в приложении не показывается в мастере записи;
- `trainer_id` услуги маппится на тренеров гибко: сначала `trainer_profiles.id`,
  затем `trainer_profiles.user_id`, иначе создаётся псевдо-тренер с именем из
  учётной записи (префикс `ext:`);
- массовая заливка расписания (пример: всем активным услугам пн–вс):

```sql
UPDATE services SET schedule = '{"days":[0,1,2,3,4,5,6],
  "time_slots":[{"time":"10:00","capacity":8},{"time":"18:00","capacity":10}"}}'::jsonb
WHERE is_active = TRUE;
```

### Права роли client (чек-лист развёртывания)

Мини-приложение рассчитано на роль `client`. Выданные права чтения
(GRANT'ом в `role_permissions`):

```
services.read, visits.read, subscriptions.read, wallet.read,
tariffs.read, clients.read, trainers.read, warehouse.read
```

(без админских: users/payments/audit/…). Право `wallet.read` дополнительно
управляет колонками «Баланс»/«Бонусы» в десктопе («Клиенты»).

### Развёртывание и файлы

| Файл | Роль |
|---|---|
| `static/miniapp/index.html` | UI приложения (обновляется bind-mount'ом, без пересборки) |
| `app/api/v1/miniapp_config.py` | Все эндпоинты модуля + движок бонусов + задача напоминаний |
| `app/api/v1/club_params.py` | Реестр параметров (DEFAULT_PARAMS) |
| `app/services/bot_scenarios.py` | Сценарии бота (старт → приглашение в приложение) |
| `app/integrations/max/service.py` | Клиент Bot API MAX (отправка сообщений) |
| `app/api/v1/visits.py` | Hook начисления бонусов за посещение (в `entry()`, `manual_add_visit()`) |

Рабочий цикл правок: Windows (репо) → `git push` → сервер `git pull` →
`docker compose -f docker-compose.test.yml up -d --build api` (быстрая, тяжёлые
слои закэшированы).

---

# ЧАСТЬ 2. МОДУЛЬ «ЮKassa»

## 2.1. Назначение

Приём оплаты пополнения кошелька клиента через ЮKassa (Smart Payment):
клиент в приложении вводит сумму → оплачивает на hosted-странице ЮKassa →
webhook от ЮKassa → автоматическое зачисление баланса + бонусы + push в MAX.

## 2.2. Пользовательская документация

### Для администратора клуба (настройка)

1. **Получить ключи.** Кабинет ЮKassa (yookassa.ru) → тестовый или боевой режим:
   `shopId` + «Секретный ключ».
2. **Вписать ключи.** Десктоп → «Параметры клуба» → «Настройки приложения»:
   поля «ЮKassa shopId», «ЮKassa секретный ключ» (или двойной клик по
   `YK_SHOP_ID` / `YK_SECRET_KEY` в «Временных параметрах»).
3. **Переключить провайдера.** «Провайдер пополнения кошелька» → `yookassa`
   (параметр `WALLET_PAY_PROVIDER`). Для отката — `test`.
4. **Настроить webhook в кабинете ЮKassa:**
   `https://fixintel.ru/api/v1/yookassa/webhook` (событие `payment.succeeded`).
5. Дополнительно: `WALLET_TOPUP_MIN` (мин. сумма), `WALLET_BONUS_PERCENT`
   (или правило «Бонусы → Пополнение»).

### Для клиента

Меню → «Баланс • Бонусы» → «+ Пополнить баланс» → сумма (не меньше минимума) →
переход на страницу оплаты ЮKassa → оплата → возврат в приложение. Баланс
зачисляется автоматически webhook'ом (обычно секунды); приходит push
«💳 Кошелёк пополнен: N ₽ (бонусы +M)». При сбое оплаты деньги не списываются.

### Тестирование без реальных денег

- Режим `test` (провайдер по умолчанию): мгновенное зачисление без оплаты — для
  демонстраций.
- Режим `yookassa` с тестовыми ключами: оплата тестовой картой
  `5555 5555 5555 4444` (успех), `5555 5555 5555 4477` (отказ: недостаток средств);
  срок — любой будущий, CVC — любой, 3‑DS код 12345. Отмена оплаты — закрыть окно оплаты.

## 2.3. Техническая документация

### Создание платежа

`POST /api/v1/miniapp/wallet/topup` (JWT) → при `provider=yookassa`:
`app/services/yookassa_service.py::create_payment(amount, description, return_url,
metadata)` → `POST https://api.yookassa.ru/v3/payments`, Basic Auth
`base64(shop_id:secret_key)`, тело:

```json
{
  "amount": {"value": "100.00", "currency": "RUB"},
  "confirmation": {"type": "redirect", "return_url": "<app url>"},
  "capture": true,
  "description": "Пополнение кошелька",
  "metadata": {"wallet_topup": "1", "client_id": "<uuid>", "bonus_percent": "7"}
}
```

Ответ приложению: `{ok, provider: "yookassa", payment_url, payment_id}` —
клиент редиректится на `confirmation_url`. Ключи берутся из `club_params`
(`YK_SHOP_ID`/`YK_SECRET_KEY`), fallback — env.

### Webhook

`POST /api/v1/yookassa/webhook` (`app/api/v1/yookassa.py`).

**Проверка подлинности — две ветки:**

1. **Локальные/тестовые вызовы** — заголовок `X-YooKassa-Signature`:
   `HMAC_SHA256(key=YK_SECRET_KEY or WEBHOOK_SECRET, msg=raw_body)`.
2. **Настоящие уведомления ЮKassa** (заголовка нет): сверка через API —
   `GET /v3/payments/{id}` и зачисление только при `status == "succeeded"`
   + совпадении `metadata`. Подделать без ключей магазина невозможно.

**Антидубль:** событие фиксируется в `yookassa_webhook_events.event_key`
(`{event}:{payment_id}`), повторная доставка отвечает `{"status": "already"}`.
Таблица создаётся автоматически (`CREATE TABLE IF NOT EXISTS`) при первом вызове.

**Ветка пополнения кошелька** (`metadata.wallet_topup == "1"`):
`_wallet_credit(db, client_id, amount, 0)` — зачисление `wallets.balance` +
запись `wallet_transactions` (все NOT NULL-колонки заполняются автоматически) →
`award_bonus(db, client_id, "topup", amount)` (правила; fallback —
`WALLET_BONUS_PERCENT`) → push в MAX → ответ
`{status, wallet_credited, balance, bonuses_added}`.

### Диаграмма потока

```
Клиент (MAX)                FastAPI                     ЮKassa
    │ POST /miniapp/wallet/topup │                          │
    │◄──── payment_url ──────────│                          │
    │──────── оплата на hosted-странице ЮKassa ───────────►│
    │◄────────────────── return_url (в приложение) ────────│
    │                            │◄── POST /yookassa/webhook│
    │                            │  (verify by API)         │
    │                            │ wallets + bonus_rules    │
    │◄── push «💳 Пополнен» ─────│──► MAX Bot API           │
```

### Безопасность

- JWT на всех клиентских эндпоинтах кошелька; баланс — только своей карточки.
- Секретный ключ хранится в club_params БД (не в коде); в десктопе поле с маской.
- Webhook без верификации ничего не зачисляет (две ветки проверки выше).
- Антидубль по `event_key`; перепроверка статуса платежа по API.

### Параметры конфигурации

| Ключ | Назначение |
|---|---|
| `WALLET_PAY_PROVIDER` | test / yookassa / sbp |
| `YK_SHOP_ID`, `YK_SECRET_KEY` | Ключи магазина |
| `WALLET_TOPUP_MIN` | Мин. сумма, ₽ (422 при меньшей) |
| `WALLET_BONUS_PERCENT` | Fallback-процент бонусов |
| Env `YOOKASSA_WEBHOOK_SECRET` | Ключ HMAC для локальной симуляции (default `test-webhook-secret`) |

### Тестирование webhook без оплаты (симуляция)

```bash
SECRET=$(docker exec deploy-api-1 python -c "from app.api.v1.club_params import get_param; print(get_param('YK_SECRET_KEY','') or 'test-webhook-secret')")
CID=$(docker exec deploy-api-1 python -c "
from sqlalchemy import text
from app.db.session import engine
with engine.connect() as c:
    print(c.execute(text(\"SELECT id::text FROM clients WHERE phone LIKE '%9263627632'\")).scalar())")
BODY="{\"event\":\"payment.succeeded\",\"object\":{\"id\":\"wallet-test-001\",\"amount\":{\"value\":\"100.00\"},\"metadata\":{\"wallet_topup\":\"1\",\"client_id\":\"$CID\",\"bonus_percent\":\"7\"}}}"
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')
curl -s -X POST http://192.168.101.182/api/v1/yookassa/webhook \
  -H "X-YooKassa-Signature: $SIG" -H 'Content-Type: application/json' -d "$BODY"
# Ожидание: {"status":"ok","wallet_credited":100.0,"balance":..., "bonuses_added":7.0}
```

### Файлы модуля

| Файл | Роль |
|---|---|
| `app/services/yookassa_service.py` | Клиент API ЮKassa (create/get/cancel/refund), чтение ключей из club_params |
| `app/api/v1/yookassa.py` | Webhook: верификация (HMAC / verify-by-API), зачисление кошелька, антидубль |
| `app/api/v1/miniapp_config.py` | `/miniapp/wallet/topup` (ветки test/yookassa), `_wallet_credit` |
| Десктоп `club_params_tab.py` | Поля провайдера/ключей в «Настройки приложения» |

### Известные ограничения и roadmap

- Провайдер `sbp` — заглушка (503) до получения банковских сертификатов (Альфа-Банк: mTLS + RSA-подпись тела).
- Возвраты по пополнению кошелька — через `create_refund` сервиса, UI не подключён.
- ЮKassa шлёт уведомления с задержкой до нескольких минут — UI ждёт webhook,
  при возврате из hosted-страницы баланс может обновиться с небольшой паузой.
- `return_url` в create_payment захардкожен на `https://fixintel.ru/static/miniapp/index.html`
  (для белого домена клуба вынести в параметр).
- Лимит MAX Bot API — 30 запросов/мин; рассылки больших баз делать с паузами.

## Roadmap обоих модулей

1. **Отмена записи клиентом** в приложении (кнопка у записи, окно `CANCEL_WINDOW_HOURS`).
2. События бонусов `purchase` (магазин) и `review` (отзывы) — hook'и их точек создания.
3. Провайдер `sbp` (Альфа-Банк): mTLS + RSA-подпись, после получения сертификатов.
4. Уведомление клиенту о результате оплаты в момент возврата (poll статуса платежа).
5. Тенантность/белый домен: return_url, webhook URL, брендинг из White-label.
