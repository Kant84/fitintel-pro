# FitIntel Pro — Полная документация
## Версия 1.4.0 | Дата: 22.08.2026

---

## 1. Общее описание

**FitIntel Pro** — интеллектуальная система управления фитнес-клубом с AI-аналитикой, распознаванием лиц (Face ID), модулем бухгалтерии и платежей, DAL-интеграцией устройств, документооборотом и ролевой моделью доступа.

**Архитектура:**
- **Бэкенд** — FastAPI (Python), СУБД PostgreSQL/SQLite, порт `8001`
- **Тонкий клиент** — PyQt6 desktop-приложение (Windows): боковое меню по роли, тёмная/светлая тема, масштабирование, файловые логи
- **AI-модули** — прогноз оттока, сегментация рисков, прогноз выручки, тепловая карта посещаемости
- **DAL (Device Abstraction Layer)** — универсальный интерфейс подключения оборудования (турникеты, камеры, считыватели)

---

## 2. Системные требования

### Сервер (бэкенд)
| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| ОС | Windows 10/11, Linux | Windows Server / Ubuntu 22.04 |
| Python | 3.10+ | 3.11–3.12 |
| RAM | 4 GB | 8 GB |
| Диск | 10 GB SSD | 50 GB SSD |
| Сеть | localhost / LAN | статический IP |

### Тонкий клиент
| Параметр | Требование |
|----------|------------|
| ОС | Windows 10/11 |
| Python | 3.10+ |
| Пакеты | PyQt6, requests, matplotlib |
| RAM | 4 GB |
| Разрешение | 1280×800 минимум |
| Сеть | Доступ к серверу по HTTP (порт 8001) |

---

## 3. Установка

### 3.1. Бэкенд (сервер)

```powershell
git clone https://github.com/Kant84/fitintel-pro.git
cd fitintel-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
```

**Важно:** в `.env` должны быть корректные `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM` (HS256), `ACCESS_TOKEN_EXPIRE_MINUTES`.

> ⚠️ Файл `.env` нельзя коммитить в git. Если он попал в историю репозитория — все секреты из него нужно сменить (ротация) перед продом.

### 3.2. Тонкий клиент (desktop)

```powershell
cd fitintel-desktop
pip install PyQt6 requests matplotlib
```

Проверка синтаксиса всех файлов:
```powershell
Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object {
    python -c "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" $_.FullName
}
```

---

## 4. Запуск

### 4.1. Бэкенд

```powershell
cd C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI
$env:PYTHONPATH = "."
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Проверка: `curl http://127.0.0.1:8001/openapi.json`

### 4.2. Тонкий клиент

```powershell
cd C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\fitintel-desktop
& "C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\.venv\Scripts\python.exe" main.py
```

**Тестовые учётные данные:** логин `my_new_username`, пароль `TestPass123!`

**Запоминание логина:** на окне входа есть чекбокс «Запомнить меня» — логин и пароль сохраняются в `client_settings.json` рядом с клиентом.
> ⚠️ Пароль хранится в открытом виде — только для dev. Перед продом заменить на Windows Credential Manager / DPAPI.

---

## 5. Ролевая модель и права доступа

### 5.1. Роли

| Роль | Код | Описание |
|------|-----|----------|
| Суперадминистратор | `superadmin` | Полный доступ, настройка экранов ролей, лицензия |
| Администратор | `admin` | Все рабочие экраны, пользователи, устройства |
| Менеджер | `manager` | Продажи, клиенты, платежи, аналитика |
| Тренер | `trainer` | Расписание, свои клиенты, посещения |
| Ресепшен | `reception` | Входы/выходы, просмотр клиентов, Face ID |

Алиасы ролей на бэкенде: `administrator→admin`, `super_admin→superadmin` (модуль UI-Config).

### 5.2. Экраны тонкого клиента (18 штук)

Меню — **вертикальный список слева** (sidebar) с горизонтальными подписями. Состав меню приходит с сервера (`GET /ui-config/my`) в зависимости от роли.

| Экран | Код | superadmin | admin | manager | trainer | reception |
|-------|-----|:---:|:---:|:---:|:---:|:---:|
| Главная | dashboard | ✅ | ✅ | ✅ | ⚠️ | ❌ |
| Клиенты | clients | ✅ | ✅ | ✅ | ✅* | ✅ |
| Абонементы | subscriptions | ✅ | ✅ | ✅ | ❌ | ❌ |
| Входы/Выходы | visits | ✅ | ✅ | ✅ | ❌ | ✅ |
| Расписание | schedule | ✅ | ✅ | ✅ | ✅ | ❌ |
| Тарифы | tariffs | ✅ | ✅ | ✅ | ❌ | ❌ |
| Платежи | payments | ✅ | ✅ | ✅ | ❌ | ❌ |
| Отчёты | reports | ✅ | ✅ | ✅ | ❌ | ❌ |
| Аналитика | analytics | ✅ | ✅ | ✅ | ❌ | ❌ |
| Документы | documents | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| Устройства | devices | ✅ | ✅ | ❌ | ❌ | ❌ |
| Пользователи | users | ✅ | ✅ | ❌ | ❌ | ❌ |
| Роли и права | roles | ✅ | ✅ | ❌ | ❌ | ❌ |
| Face ID | face_id | ✅ | ✅ | ❌ | ❌ | ✅ |
| Лицензия | license | ✅ | ❌ | ❌ | ❌ | ❌ |
| Настройки | settings | ✅ | ✅ | ✅ | ✅ | ✅ |
| Экраны ролей | ui_config | ✅ | ❌ | ❌ | ❌ | ❌ |
| Мастер установки | setup | ✅ | ❌ | ❌ | ❌ | ❌ |

> ✅* — тренер видит только своих клиентов. Матрица настраивается суперадмином через «Экраны ролей».

---

## 6. Экраны тонкого клиента — подробно

### 6.0. Общие элементы интерфейса

- **Боковое меню слева** — список экранов по роли; ширина 180px, подписи горизонтально.
- **Меню «Вид»** — Светлая/Тёмная тема (весь интерфейс перекрашивается, включая таблицы и графики).
- **Масштабирование** — `Ctrl +` увеличить, `Ctrl -` уменьшить шрифт; также кнопки А−/А+ в «Настройках».
- **Логи** — «Настройки → Логи»: открыть папку `logs/`, последние 10 ошибок. Файл: `logs/client_YYYYMMDD.log`; логируются все API-ошибки (4xx/5xx) и необработанные исключения.

### 6.1. Главная (Dashboard)

- KPI-карточки: посещения сегодня, выручка сегодня, прогноз недели, клиенты в риске.
- **График выручки** (matplotlib, встроенный): зелёная линия — история, оранжевый пунктир — AI-прогноз (`POST /analytics/forecast`).
- **Тепловая карта посещаемости** 7×24 (`/analytics/ai/heatmap`).
- **Кнопка «Веб-график»** — открывает интерактивный Chart.js-дашборд (`/analytics/dashboard-chart`) в браузере.
- Таблица «Топ клиентов с риском оттока» с ФИО.

### 6.2. Клиенты

- Таблица: ФИО, телефон, email, пол, категория, статус.
- **＋ Добавить**, **✎ Изменить** (или двойной клик), **⊘ Деактивировать**, **🗑 Удалить** (с подтверждением).
- Enum-поля строго: gender `MALE/FEMALE`, категория `ADULT/CHILD/VIP/STAFF`, статус `ACTIVE/...` (uppercase) — иначе 500 на списке (см. 9.3).

### 6.3. Абонементы

- **＋ Продать абонемент** — выбор клиента и тарифа.
- **❄ Заморозить** (дата + причина), **▶ Разморозить**.

### 6.4. Входы/Выходы

- Таблица посещений с **ФИО и телефоном** (резолв через `/clients/`).
- **«Ручной вход»** — регистрация визита вручную (клиент, способ, зона).
- Статистика: сегодня / неделя / месяц.

### 6.5. Платежи

Две подвкладки: **«Платежи клиента»** и **«Проводки (бухгалтерия)»**.

Действия (кнопки сверху):
| Кнопка | Что делает | API |
|--------|-----------|-----|
| ＋ Провести платёж | Сумма, способ (CASH/CARD/SBP/TRANSFER/ONLINE/QR/BALANCE/...), направление, категория, комментарий | `POST /payments/` |
| ✓ Подтвердить | Подтверждение выбранного платежа | `POST /payments/{id}/complete` |
| ↩ Возврат | Полный или частичный возврат (причина обязательна) | `POST /payments/{id}/refund` |
| ✕ Отмена платежа | Отмена = возврат полной суммы с причиной «Отмена платежа» | `POST /payments/{id}/refund` |
| ⇩ Экспорт CSV | Выгрузка платежей в файл | `POST /reports/payments/export` |

> ⚠️ Отдельного endpoint «отмена» в API нет — отмена оформляется возвратом полной суммы. Для прода рекомендуется завести статус CANCELLED, чтобы отмены не смешивались с возвратами в отчётах.

### 6.6. Документы

- Шаблоны документов, список документов по клиенту.
- **«Сгенерировать»** — документ из шаблона (`POST /documents`).
- Скачивание: `GET /documents/{id}/download?format=pdf|docx`.
- Загрузка файлов (сканы договоров/чеков) — endpoint добавляется (см. PROD_NOTES).

### 6.7. Устройства (DAL)

- Таблицы драйверов и устройств.
- **«Найти устройства»** — `POST /dal/devices/discover`.
- **«Добавить вручную»** — драйвер + имя + строка подключения.

### 6.8. Остальные экраны

- **Расписание** — расписание тренеров (`/services/trainer-schedule`).
- **Тарифы** — список + «Создать тариф» (код, имя, цена, длительность).
- **Отчёты** — календарь отчётности (`/reporting/calendar`).
- **Аналитика** — AI-графики и веб-дашборды.
- **Пользователи** — список + «Создать пользователя».
- **Роли и права** — RBAC-матрица (`/rbac/roles-matrix`).
- **Face ID** — кнопки «Движок Face ID», «Шаблоны», симуляция verify (см. 7.3).
- **Лицензия** — статус, срок, лимиты (только superadmin).
- **Экраны ролей** — редактор матрицы видимости (только superadmin, защита от самоблокировки).
- **Мастер установки** — чек-лист шагов первичной настройки (`/setup/status`).
- **Настройки** — тема, размер шрифта, проверка сервера, логи.

---

## 7. Настройка

### 7.1. Первоначальная настройка

1. Создать суперадминистратора → 2. Войти в клиент → 3. Проверить лицензию → 4. Настроить экраны ролей → 5. Создать пользователей → 6. Подключить устройства.

### 7.2. Настройка экранов по ролям

UI: «Экраны ролей» → роль → чекбоксы → «Сохранить». Изменения видны после перелогина.
API: `GET /ui-config/roles`, `PUT /ui-config/roles/{role}/screens`, `POST /ui-config/roles/{role}/reset`, `GET /ui-config/my`.

### 7.3. Face ID

- `POST /face-id/register` — регистрация: `{client_id, photo}` (photo = base64 JPEG/PNG).
- `POST /face-id/verify` — проверка: **`{photo}`** (base64). Внимание: полей `face_encoding`/`terminal_id` в схеме нет — старые клиенты получают 422.
- `POST /face-id/turnstile` — `{photo, device_id, zone?}` для турникета.
- `GET /face-id/engine/info` — статус движка; `POST /face-id/anti-spoofing` — `{photo}`.
- Вкладка «Face ID» в клиенте: статус движка, список шаблонов, симуляция verify (тестовое фото 1×1 — только для проверки связи, реальное распознавание требует фото с камеры).

### 7.4. Файл настроек клиента

`fitintel-desktop/client_settings.json`:
```json
{"theme": "dark|light", "font_size": 10, "remember_login": true,
 "saved_login": "...", "saved_password": "..."}
```

---

## 8. API — ключевые эндпоинты

### Аутентификация
```
POST /api/v1/auth/login          # JSON {login, password} → {access_token}
GET  /api/v1/auth/me
```

### Клиенты / Посещения / Абонементы
```
GET/POST/PUT/DELETE /api/v1/clients/...
GET  /api/v1/visits/             # {items: [...]}
POST /api/v1/visits/manual       # {client_id, entry_time, access_method, zone}
POST /api/v1/subscriptions/      # продажа; freeze/unfreeze — заморозка
```

### Платежи и чеки
```
POST /api/v1/payments/                     # {amount, payment_method, client_id?, payment_direction?, payment_category?, notes?}
GET  /api/v1/payments/client/{client_id}
POST /api/v1/payments/{id}/complete
POST /api/v1/payments/{id}/refund          # {reason, amount?, refund_to_balance?}
POST /api/v1/reports/payments/export       # {format: "csv", date_from?, date_to?, client_id?}
POST /api/v1/receipts/                     # {payment_id, items, receipt_type?, customer_email?}
GET  /api/v1/receipts/{id}/pdf             # PDF чека
POST /api/v1/receipts/{id}/print|send|fiscalize
```

### Бухгалтерия
```
GET/POST /api/v1/accounting/entries
GET  /api/v1/accounting/balance-sheet/{period} | cash-flow/{period} | osv/{period}
POST /api/v1/accounting/pko | rko | sale | purchase | manual-entry
GET  /api/v1/accounting/export/1c | export/buh
```

### Документы
```
GET/POST /api/v1/documents                 # {type, client_id, template_id?, data?}
GET  /api/v1/documents/templates
GET  /api/v1/documents/{id}/download?format=pdf
POST /api/v1/documents/{id}/sign | send-email | print
```

### Доступ, замки, ключи (СКУД)
```
POST /api/v1/access/check|grant|open|exit|override   # {credential, device_id, ...}
POST /api/v1/access/manual-open                      # {device_id, reason}
POST /api/v1/access/emergency-unlock
GET  /api/v1/access/logs
POST /api/v1/credentials/card                        # {client_id, card_number, valid_until?}
POST /api/v1/credentials/bracelet                    # {client_id, bracelet_id, valid_until?}
POST /api/v1/credentials/rfid                        # {client_id, credential_value}
POST /api/v1/credentials/{id}/block|unblock
GET/POST /api/v1/lockers                             # шкафчики
POST /api/v1/lockers/{id}/assign|open|block|release
```

### Face ID
```
POST /api/v1/face-id/register      # {client_id, photo}
POST /api/v1/face-id/verify        # {photo}
POST /api/v1/face-id/turnstile     # {photo, device_id}
GET  /api/v1/face-id/engine/info
POST /api/v1/face-id/anti-spoofing # {photo}
```

### AI-Аналитика
```
GET  /api/v1/analytics/dashboard
POST /api/v1/analytics/forecast            # {metric: "revenue", days_ahead: 7}
GET  /api/v1/analytics/ai/churn | risk-segments | heatmap
GET  /api/v1/analytics/dashboard-chart     # HTML-страница Chart.js (открывать в браузере)
```

### DAL / Устройства
```
GET  /api/v1/dal/drivers | devices
POST /api/v1/dal/devices/discover          # {driver_id}
POST /api/v1/dal/devices                   # {driver_id, name, connection_string}
POST /api/v1/dal/devices/{id}/command|ping
```

### UI-Config (E51)
```
GET  /api/v1/ui-config/my | screens | roles
PUT  /api/v1/ui-config/roles/{role}/screens
POST /api/v1/ui-config/roles/{role}/reset
```

---

## 9. Распространённые ошибки и решения

### 9.1. Запуск
| Ошибка | Причина | Решение |
|--------|---------|---------|
| `SyntaxError` в .py | `\n` превратился в реальный перенос строки | Авто-чинилка: склейка строк до `ast.parse` |
| `ModuleNotFoundError: PyQt6/matplotlib` | Не тот venv (prompt `(venv)` вместо `(.venv)`) | Запускать через `& ".\.venv\Scripts\python.exe"` |
| `Connection refused` | Бэкенд не запущен | uvicorn на порту 8001 |
| Путь обрезан при запуске | Пробелы в `FitNexus AI`, потеряны кавычки | Одинарные кавычки внутри `-ArgumentList` |

### 9.2. Авторизация
| Ошибка | Причина | Решение |
|--------|---------|---------|
| 422 на входе | form-data на `/auth/token` вместо JSON на `/auth/login` | В `client.py`: `POST /auth/login`, поле `login`, `json=` |
| 401 | Токен истёк | Перелогин |

### 9.3. 500 на `/clients/` (enum-данные)
Legacy-значения в БД ломают Pydantic response_model. Миграция:
```sql
UPDATE clients SET gender='MALE'  WHERE gender IN ('МУЖСКОЙ','мужской','М','m','male');
UPDATE clients SET gender='FEMALE' WHERE gender IN ('ЖЕНСКИЙ','женский','Ж','f','female');
UPDATE clients SET client_category='ADULT' WHERE client_category IN ('ОБЫЧНАЯ','REGULAR','regular');
UPDATE clients SET client_category='STAFF' WHERE client_category IN ('terminal','staff');
UPDATE clients SET status=UPPER(status) WHERE status <> UPPER(status);
UPDATE clients SET email=CONCAT('noemail-',LEFT(id::text,8),'@fitintel.local') WHERE email IS NULL OR email NOT LIKE '%@%';
```

### 9.4. Прочее
| Ошибка | Причина | Решение |
|--------|---------|---------|
| `'str'/'dict' object has no attribute` во вкладке | API вернул `{items: [...]}` вместо list | Нормализатор `_as_list()` в client.py |
| 422 на `/face-id/verify` | Клиент слал `face_encoding` | Схема ждёт `{photo: base64}` |
| Вкладки «вертикальные»/старый вид | Изменения main_window не записались | Проверять файл Select-String после записи |

---

## 10. Структура проекта

```
FitIntel AI/
├── app/                        # Бэкенд (FastAPI)
│   ├── api/v1/                 # auth, clients, visits, payments, receipts,
│   │                           # accounting, documents, face_id, access,
│   │                           # credentials, lockers, dal, analytics, ui_config, ...
│   ├── core/  db/  main.py
├── fitintel-desktop/           # Тонкий клиент (PyQt6)
│   ├── main.py
│   ├── app_logging.py          # файловые логи logs/client_YYYYMMDD.log
│   ├── client_settings.json    # тема, шрифт, запомненный логин
│   ├── api/client.py           # HTTP-клиент (+E55-методы: payments, face, docs, lockers)
│   └── windows/
│       ├── theme.py            # центральная тема (тёмная/светлая)
│       ├── form_dialog.py      # универсальный диалог форм
│       ├── login_window.py     # вход + запоминание логина
│       ├── main_window.py      # sidebar-меню + вкладки по роли
│       └── *_tab.py            # 18 экранов
├── doc/                        # Документация (этот файл)
├── scripts/temp/               # Диагностические скрипты
├── PROD_NOTES.md               # Предпродовые замечания
└── requirements.txt
```

---

## 11. Чек-лист администратора

- [ ] Бэкенд отвечает на `localhost:8001/openapi.json`
- [ ] Миграции БД применены, enum-данные вычищены (9.3)
- [ ] Вход работает, логин запоминается
- [ ] Все экраны роли открываются без ошибок
- [ ] Платежи: провести → подтвердить → возврат → отмена → экспорт CSV
- [ ] Face ID: движок отвечает, verify не даёт 422
- [ ] Экраны ролей настроены для всех ролей
- [ ] Лицензия активна
- [ ] Бэкап БД настроен
- [ ] Секреты из `.env` сменены перед продом

---

## 12. Контакты

- **Репозиторий:** https://github.com/Kant84/fitintel-pro.git
- **Версия:** 1.4.0 | **Локальный путь:** `C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI`
