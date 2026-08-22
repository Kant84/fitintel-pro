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


---

# FitIntel Pro — Расширенное руководство эксплуатации
## Дополнение к полной документации v1.4.0 | 22.08.2026

---

## Содержание дополнения

12. Подробная работа с каждой вкладкой (пошагово)
13. Безопасность и защита данных
14. Обновление системы (бэкенд + клиент)
15. Резервное копирование и аварийное восстановление
16. Face ID — полная инструкция по настройке
17. DAL — подключение оборудования
18. Диагностика и отладка (скрипты, логи)
19. Работа с OpenAPI / Swagger
20. Настройка окружения (.env подробно)
21. FAQ — ответы на частые вопросы
22. Глоссарий терминов
23. История изменений (CHANGELOG)

---

## 12. Подробная работа с каждой вкладкой

### 12.1. Экран авторизации (Login Window)

**Что видит пользователь:**
- Поле «Логин», поле «Пароль», кнопка «Войти»
- **Чекбокс «Запомнить меня»** — логин и пароль сохраняются в `client_settings.json` и подставляются при следующем запуске
- Статус подключения к серверу

**Пошагово:**
1. Убедитесь, что бэкенд запущен (порт 8001)
2. Введите логин/пароль, при желании отметьте «Запомнить меня»
3. «Войти» или Enter → откроется главное окно с меню экранов слева (состав — по вашей роли)
4. Ошибка 422 — клиент шлёт не тот формат (см. 9.2 основной документации)
5. Ошибка 401 — неверный логин/пароль

> ⚠️ Сохранённый пароль лежит в `client_settings.json` открытым текстом — это dev-режим. Перед продом — переход на Windows Credential Manager (см. PROD_NOTES.md).

### 12.2. Главная (Dashboard Tab)

**Ряд KPI-карточек (5 штук):**

| Карточка | Откуда данные | Что делать если «—» |
|----------|---------------|---------------------|
| Посещений сегодня | GET /analytics/dashboard → attendance_today | Проверить, что визиты записываются в БД |
| Выручка сегодня | GET /analytics/dashboard → revenue_today | Проверить accounting_entries за сегодня |
| Прогноз недели | GET /analytics/dashboard → forecast_week_revenue | AI-модель не обучена — нужны данные за 30+ дней |
| Клиентов в риске | GET /analytics/dashboard → churn_risk_count | Проверить GET /analytics/ai/churn |
| К прошлой неделе | GET /analytics/dashboard → vs_last_week | Недостаточно исторических данных |

**Инфо-панель «Сегменты риска»:**
- Жёлтый фон, показывает распределение high/medium/low
- Если пусто — AI-аналитика ещё не запускалась или данных мало

**Таблица «AI: клиенты с риском оттока»:**
- Загружается автоматически при открытии вкладки
- Для обновления — кнопка «Обновить» или F5
- Красные строки = требуют внимания менеджера (позвонить клиенту)

---

### 12.3. Клиенты (Clients Tab)

**Интерфейс:**
- Панель фильтров (ФИО, телефон, статус, категория)
- Кнопки: «Добавить», «Редактировать», «Удалить», «Обновить»
- Таблица с постраничным выводом

**Пошаговое добавление клиента:**
1. Нажмите «Добавить»
2. Заполните обязательные поля:
   - Фамилия, Имя (обязательно)
   - Телефон (обязательно, уникальный)
   - Email (если пусто — система подставит noemail-{id}@fitintel.local)
   - Пол: MALE / FEMALE
   - Категория: ADULT / CHILD / VIP / STAFF
   - Статус: ACTIVE / INACTIVE / FROZEN
3. Нажмите «Сохранить»

**Важно:** Поле gender в БД должно быть строго MALE или FEMALE (uppercase).
Поле client_category — ADULT, CHILD, VIP, STAFF.
Поле status — ACTIVE, INACTIVE, FROZEN (uppercase).
Нарушение приведёт к ошибке 500 при загрузке списка.

---

### 12.4. Входы/Выходы (Visits Tab)

**Как данные попадают в таблицу:**
1. Ручной ввод: Ресепшен нажимает «Новый визит»
2. Face ID: Камера распознаёт лицо → автоматический POST /visits/
3. Карта/Турникет: DAL-устройство отправляет событие

**Поиск:** Работает по ФИО, телефону, статусу, способу входа. Регистр неважен.

**Цветовая индикация статуса:**
- Зелёный (#059669) — ACTIVE (клиент внутри)
- Серый (#64748b) — COMPLETED (визит завершён)

---

### 12.5. Абонементы (Subscriptions Tab)

**Функционал:**
- Просмотр всех абонементов
- Фильтрация по статусу (active / expired / frozen)
- Привязка к клиенту
- Продление / заморозка

---

### 12.6. Платежи (Payments Tab)

**Две подвкладки:** «Платежи клиента» (операции) и «Проводки (бухгалтерия)» (журнал `accounting/entries`).

**Провести платёж:**
1. Выберите клиента в списке сверху
2. «＋ Провести платёж» → сумма, способ оплаты (CASH, CARD, SBP, TRANSFER, ONLINE, SUBSCRIPTION, QR, BALANCE, OTHER), направление и категория (необязательно), комментарий
3. `POST /payments/` → платёж появляется в таблице

**Подтвердить:** выделите платёж → «✓ Подтвердить» (`POST /payments/{id}/complete`).

**Возврат:** выделите платёж → «↩ Возврат» → укажите причину (обязательно) и сумму (пусто = полная). `POST /payments/{id}/refund`.

**Отмена платежа:** выделите платёж → «✕ Отмена платежа» → подтверждение → оформляется возврат полной суммы с причиной «Отмена платежа».
> ⚠️ Отдельного endpoint отмены в API нет — отмена технически является возвратом. В отчётах отличайте по полю reason.

**Экспорт:** «⇩ Экспорт CSV» → выбор файла → выгрузка платежей клиента (`POST /reports/payments/export`, format=csv). Для бухгалтерии также доступны `GET /accounting/export/1c` и `/accounting/export/buh`.

**Сверка:** итог проводок должен совпадать с Z-отчётом кассы; расхождения ищите среди записей source='manual'.

### 12.7. Пользователи (Users Tab)

**Доступ:** superadmin, admin

**Функции:** Создание пользователя, назначение ролей, активация/деактивация, сброс пароля.

**Важно:** Пароль минимум 8 символов, 1 цифра, 1 буква верхнего регистра.
Нельзя удалить единственного superadmin.
При деактивации сессии немедленно становятся невалидными.

---

### 12.8. Устройства (Devices Tab)

**Два блока:**
- Подключённые устройства: Название, тип, строка подключения, драйвер, статус
- Установленные драйверы: Пакет, версия, статус, дата установки

**Добавление устройства:**
1. Установить драйвер: POST /dal/drivers/{package}/install
2. Обнаружить устройство: POST /dal/drivers/{package}/discover
3. Устройство появится в таблице

**Типичные драйверы:**
- fitintel-dal-faceid — камера распознавания лиц
- fitintel-dal-turnstile — турникет
- fitintel-dal-cardreader — считыватель карт

---

### 12.9. Face ID

**Схема API (важно):** verify принимает `{"photo": "<base64>"}` — никаких `face_encoding`/`terminal_id`. Нарушение = 422.

**Вкладка содержит:**
- «Движок Face ID» — статус движка (`GET /face-id/engine/info`)
- «Шаблоны (список)» — зарегистрированные биометрические шаблоны (`GET /face-id`)
- «Симуляция: verify / Разрешить / Запретить» — проверка связи с движком тестовым фото 1×1 (реальное распознавание требует фото с камеры)
- Ответ сервера показывается в панели деталей (JSON)

**Регистрация нового лица (API):**
```
POST /face-id/register  {"client_id": "...", "photo": "<base64 JPEG/PNG>"}
```
Требования к фото: лицо в центре, хорошее освещение, мин. 640×480.

**Распознавание на турникете:**
```
POST /face-id/turnstile  {"photo": "<base64>", "device_id": "...", "zone": "..."}
```

**Anti-spoofing:** `POST /face-id/anti-spoofing {"photo": "..."}` — проверка, что перед камерой живой человек, а не фото с экрана.

**Безопасность:**
- Фото хранятся в File Storage (не в БД)
- Шаблоны — векторы, обратное восстановление фото невозможно
- Face ID — только собственный/self-hosted движок; облачные сервисы распознавания лиц (FindFace/NtechLab) не используются

### 12.10. Лицензия (License Tab)

**Доступ:** только superadmin

**Информация:** Тип лицензии, дата активации и окончания, количество устройств/пользователей, статус.

**При просрочке лицензии:**
- Система переходит в режим «только чтение»
- Нельзя создавать новых клиентов, абонементы, визиты
- Дашборд и аналитика остаются доступными

---

### 12.11. Экраны ролей (UI-Config Tab)

**Доступ:** только superadmin

**Интерфейс:**
- Выпадающий список ролей
- Таблица: колонки «Виден» (чекбокс), «Экран», «Код»
- Кнопки: «Сохранить», «Сбросить к умолчаниям», «Обновить»

**Пошаговая настройка:**
1. Выберите роль (например, manager)
2. Отметьте галочками нужные экраны
3. Нажмите «Сохранить»
4. Пользователи с этой ролью увидят изменения после перелогина

**Защита от самоблокировки:**
У superadmin экран «Экраны ролей» всегда включён (чекбокс disabled).
Это предотвращает ситуацию, когда superadmin случайно закрывает себе доступ.

---

### 12.12. Настройки (Settings Tab)

**Разделы клиента:**
- **Тема** — Светлая / Тёмная (перекрашивается весь интерфейс: меню, таблицы, карточки, графики). Также: меню «Вид» в главном окне.
- **Размер шрифта** — кнопки А− / А+; глобально: `Ctrl +` и `Ctrl -` в любом экране.
- **Проверка сервера** — пинг бэкенда.
- **Логи** — кнопка «Открыть папку логов» (`logs/`) и просмотр последних 10 ошибок прямо на экране.

Настройки сохраняются в `client_settings.json` (тема, шрифт, запомненный логин).

---

## 13. Безопасность и защита данных

### 13.1. Аутентификация

- JWT-токены: Bearer схема, срок жизни настраивается в .env (ACCESS_TOKEN_EXPIRE_MINUTES)
- Рекомендуемое значение: 60 минут для desktop-клиента
- Токен хранится в памяти приложения (не в реестре, не в файле)
- При выходе: api.clear_token()

### 13.2. Пароли

- Хранятся в виде bcrypt-хешей (never plaintext)
- Требования: минимум 8 символов, 1 цифра, 1 буква верхнего регистра
- Рекомендуется смена пароля каждые 90 дней

### 13.3. HTTPS (для production)

```nginx
server {
    listen 443 ssl;
    server_name fitintel.example.com;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 13.4. Защита БД

Не используйте пользователя postgres/root для приложения.
Создайте отдельного пользователя с ограниченными правами:

```sql
CREATE USER fitintel_app WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE fitintel TO fitintel_app;
GRANT USAGE ON SCHEMA public TO fitintel_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fitintel_app;
```

### 13.5. Аудит

- Все действия пользователей логируются в таблицу audit_logs
- Содержит: user_id, action, timestamp, ip_address, details
- Хранится 1 год (настраивается)

---

## 14. Обновление системы

### 14.1. Обновление бэкенда

```powershell
# 1. Остановить текущий процесс бэкенда
# 2. Сделать бэкап БД
# 3. Обновить код
cd C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI
git pull origin main

# 4. Обновить зависимости
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 5. Применить миграции
alembic upgrade head

# 6. Запустить
$env:PYTHONPATH = "."
python -m app.main
```

### 14.2. Обновление тонкого клиента

```powershell
cd C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\fitintel-desktop
git pull origin main

# Проверить синтаксис
Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object {
    python -c "import ast; ast.parse(open(sys.argv[1], encoding='utf-8').read())" $_.FullName
}

# Запустить
python main.py
```

### 14.3. Совместимость версий

| Версия клиента | Версия бэкенда | Совместимость |
|----------------|----------------|---------------|
| 1.3.x | 1.3.x | Полная |
| 1.3.x | 1.2.x | Частичная |
| 1.2.x | 1.3.x | Не гарантируется |

Правило: Клиент и бэкенд должны иметь одинаковую минорную версию.

---

## 15. Резервное копирование и аварийное восстановление

### 15.1. Автоматический бэкап (рекомендуется)

```powershell
# backup.ps1 — добавьте в Планировщик задач Windows
$date = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupDir = "C:\Backups\FitIntel"
New-Item -ItemType Directory -Path $backupDir -Force

# PostgreSQL
$env:PGPASSWORD = "your_db_password"
pg_dump -h localhost -U fitintel_app -d fitintel > "$backupDir\fitintel_$date.sql"

# SQLite (если используется)
Copy-Item "C:\...\app.db" "$backupDir\app_$date.db"

# Файлы (Face ID фото, лицензии)
Compress-Archive -Path "C:\...\uploads" -DestinationPath "$backupDir\uploads_$date.zip"

# Удалить бэкапы старше 30 дней
Get-ChildItem $backupDir | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item
```

### 15.2. Ручной бэкап

```powershell
$env:PGPASSWORD = "your_db_password"
pg_dump -h localhost -U fitintel_app -d fitintel > "backup_pre_update.sql"
```

### 15.3. Восстановление из бэкапа

```powershell
# Остановить бэкенд
# Восстановить БД
dropdb -U postgres fitintel
createdb -U postgres fitintel
psql -U postgres -d fitintel -f "backup_2026-08-21_10-00.sql"

# Восстановить файлы
Expand-Archive -Path "uploads_2026-08-21_10-00.zip" -DestinationPath "C:\...\uploads" -Force

# Запустить бэкенд
```

### 15.4. Проверка целостности бэкапа

```powershell
if ((Get-Item "backup.sql").Length -gt 1000) {
    Write-Host "Бэкап в порядке"
} else {
    Write-Host "ОШИБКА: бэкап повреждён!"
}
```

---

## 16. Face ID — полная инструкция по настройке

### 16.1. Требования к оборудованию

- Камера: минимум 720p, автофокус, хорошее освещение
- Рекомендуется: USB-камера с широким углом обзора
- Освещение: минимум 300 люкс, без резких теней

### 16.2. Требования к фото

| Параметр | Требование |
|----------|------------|
| Формат | JPEG, PNG |
| Разрешение | минимум 640x480 |
| Лицо | Центрировано, глаза открыты, нейтральное выражение |
| Фон | Однотонный, без посторонних лиц |
| Аксессуары | Без очков (если возможно), без головного убора |

### 16.3. Пошаговая регистрация

1. Подготовка: Убедитесь, что клиент стоит перед камерой, проверьте освещение
2. В интерфейсе: Вкладка «Face ID» → «Добавить лицо» → выберите клиента
3. Нажмите «Сделать снимок» или «Загрузить файл»
4. Система покажет предпросмотр. Если лицо не обнаружено — повторите.
5. Нажмите «Сохранить шаблон». Статус изменится на «Активно».

### 16.4. Тестирование распознавания

1. Попросите клиента встать перед камерой
2. Система должна показать его ФИО в течение 1–2 секунд
3. Если не сработало: проверьте освещение, угол, порог сходства (по умолчанию 0.85)

### 16.5. Удаление шаблона

Вкладка «Face ID» → выберите запись → «Удалить». Шаблон удаляется безвозвратно.

---

## 17. DAL — подключение оборудования

### 17.1. Архитектура DAL

```
Приложение → API /dal/drivers → Драйвер (Python пакет) → Устройство (USB/Serial/Network)
```

### 17.2. Установка драйвера

```powershell
# Через API
POST /api/v1/dal/drivers/fitintel-dal-turnstile/install

# Или вручную
pip install fitintel-dal-turnstile
```

### 17.3. Обнаружение устройства

```powershell
# Автопоиск
POST /api/v1/dal/drivers/fitintel-dal-turnstile/discover

# Ручное добавление
POST /api/v1/dal/devices
{
  "name": "Турникет главный",
  "device_type": "turnstile",
  "connection_string": "COM3:9600",
  "driver_package": "fitintel-dal-turnstile"
}
```

### 17.4. Типы подключения

| Тип | Connection String | Пример |
|-----|-------------------|--------|
| Serial | COM3:9600 | Турникет, считыватель карт |
| USB | USB:VID_1234&PID_5678 | Камера, сканер |
| Network | TCP:192.168.1.100:8080 | IP-камера, контроллер |
| Bluetooth | BLE:AA:BB:CC:DD:EE:FF | Мобильный считыватель |

### 17.5. Диагностика DAL

```powershell
GET /api/v1/dal/drivers       # Проверить статус драйвера
GET /api/v1/dal/devices/{id}/status   # Проверить статус устройства
GET /api/v1/dal/devices/{id}/logs     # Логи устройства
```

---

## 18. Диагностика и отладка

### 18.1. Диагностические скрипты

**Скрипт 1: Проверка всех endpoint**

```python
import requests
BASE = "http://127.0.0.1:8001/api/v1"
token = requests.post(f"{BASE}/auth/login", json={"login":"...","password":"..."}).json()["access_token"]
H = {"Authorization": f"Bearer {token}"}
for path in ["/clients/","/visits/","/analytics/dashboard","/accounting/entries","/users/","/dal/devices"]:
    r = requests.get(f"{BASE}{path}", headers=H)
    print(f"{path}: {r.status_code}")
```

**Скрипт 2: Диагностика 500 на /clients/**

```python
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app, raise_server_exceptions=True)
try:
    r = client.get("/api/v1/clients/", headers={"Authorization": f"Bearer {token}"})
except Exception as e:
    errs = getattr(e, "errors", None)
    if errs:
        for err in errs:
            print(f"FIELD={err.get('loc',[-1])[-1]} input={err.get('input')}")
```

**Скрипт 3: Проверка синтаксиса всех .py**

```powershell
Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object {
    python -c "import ast; ast.parse(open(sys.argv[1], encoding='utf-8').read())" $_.FullName
    if ($LASTEXITCODE -ne 0) { Write-Host "BROKEN: $($_.Name)" }
}
```

### 18.2. Логи

**Бэкенд:**
- Локация: logs/app.log (настраивается в app/core/config.py)
- Уровень: DEBUG (разработка), INFO (production), WARNING (стабильная)
- Ротация: ежедневно, хранение 30 дней

**Клиент:**
- Локация: `fitintel-desktop/logs/client_YYYYMMDD.log` (папка рядом с main.py)
- Быстрый доступ: вкладка «Настройки» → блок «Логи» → «Открыть папку» / последние 10 ошибок
- Логируются: все ответы API 4xx/5xx (через response hook), ошибки авторизации, необработанные исключения (excepthook)
- Ротация: по одному файлу на день

### 18.3. Отладка в консоли

```powershell
# Запуск бэкенда с подробным выводом
$env:LOG_LEVEL = "DEBUG"
python -m app.main

# Запуск клиента с отладкой
python main.py --debug
```

---

## 19. Работа с OpenAPI / Swagger

**URL:** http://127.0.0.1:8001/docs

**Возможности:**
- Интерактивная документация всех endpoint
- Тестирование запросов прямо в браузере
- Автоматическая генерация curl-команд
- Скачивание openapi.json

**Авторизация в Swagger:**
1. Нажмите «Authorize» (замок вверху)
2. Введите: Bearer <your_jwt_token>
3. Все запросы будут отправляться с заголовком Authorization

---

## 20. Настройка окружения (.env)

### 20.1. Полный список переменных

```ini
# === БАЗА ДАННЫХ ===
DATABASE_URL=postgresql://fitintel_app:password@localhost:5432/fitintel
# или для SQLite: DATABASE_URL=sqlite:///./app.db

# === БЕЗОПАСНОСТЬ ===
SECRET_KEY=your-super-secret-key-min-32-chars-long!!!
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# === СЕРВЕР ===
HOST=0.0.0.0
PORT=8001
DEBUG=false
LOG_LEVEL=INFO

# === EMAIL (SMTP) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=FitIntel Pro <noreply@fitintel.local>

# === SMS (опционально) ===
SMS_PROVIDER=twilio
SMS_API_KEY=your-twilio-key
SMS_FROM=+1234567890

# === FACE ID ===
FACE_ID_THRESHOLD=0.85
FACE_ID_MODEL=opencv_face_detector

# === DAL ===
DAL_AUTO_DISCOVER=true
DAL_SCAN_INTERVAL=30

# === ЛИЦЕНЗИЯ ===
LICENSE_FILE=./license.key
```

### 20.2. Генерация SECRET_KEY

```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## 21. FAQ — Ответы на частые вопросы

**Q: Окно авторизации открывается, но при входе ничего не происходит**
A: Проверьте консоль. Вероятно, 422 ошибка — клиент шлёт на /auth/token вместо /auth/login. Пропатчите api/client.py.

**Q: Главное окно открылось, но вкладка «Клиенты» пустая**
A: Скорее всего, 500 на /clients/. Запустите диагностику (раздел 18.1) и миграцию enum (раздел 9.3).

**Q: В посещениях вместо ФИО показываются ID**
A: /clients/ не загружается из-за 500. После починки клиентов ФИО появятся автоматически.

**Q: Как добавить новую роль?**
A: На текущий момент роли захардкожены. Для добавления новой роли:
1. Добавьте роль в enum на бэкенде
2. Добавьте в TAB_REGISTRY и DEFAULT_TABS в main_window.py
3. Настройте права в ui_config_tab.py
4. Пересоберите клиента

**Q: Можно ли запустить на Linux?**
A: Бэкенд — да (Python кроссплатформенный). Клиент (PyQt6) — теоретически да, но тестировался только на Windows.

**Q: Как изменить порт бэкенда?**
A: В .env установите PORT=8080, затем в api/client.py измените BASE_URL.

**Q: Face ID не распознаёт клиента**
A: Проверьте: освещение, качество фото при регистрации, порог сходства, статус камеры.

**Q: Как сбросить пароль superadmin?**
A: Через SQL: UPDATE users SET password_hash = '$2b$12$...' WHERE username = 'superadmin';
Или создайте нового superadmin через скрипт.

**Q: Где хранятся фото клиентов?**
A: В директории uploads/face_id/ (не в БД). Путь настраивается в .env.

---

## 22. Глоссарий терминов

| Термин | Описание |
|--------|----------|
| DAL | Device Abstraction Layer — слой абстракции устройств |
| JWT | JSON Web Token — токен аутентификации |
| RBAC | Role-Based Access Control — управление доступом на основе ролей |
| Churn | Отток клиентов |
| Embedding | Векторное представление лица (Face ID) |
| Enum | Перечисление — ограниченный набор допустимых значений |
| Endpoint | URL-адрес API-метода |
| Migration | Миграция БД — изменение структуры/данных |
| Pydantic | Библиотека валидации данных в Python |
| SQLAlchemy | ORM для работы с БД |
| Тонкий клиент | Приложение, которое не хранит бизнес-логику, а обращается к серверу |
| UI-Config | Модуль настройки экранов по ролям (E51) |

---

## 23. История изменений (CHANGELOG)

### v1.4.0 (22.08.2026)
- **Платежи v2**: проведение платежа, подтверждение, возврат (полный/частичный), отмена (=возврат полной суммы), экспорт CSV
- **Клиенты**: полный CRUD — добавить / изменить / деактивировать / удалить
- **Абонементы**: продажа, заморозка, разморозка; **Тарифы**: создание
- **Интерфейс**: боковое меню слева по роли, тёмная/светлая тема (theme.py), масштаб Ctrl±, запоминание логина
- **Логи клиента**: logs/client_YYYYMMDD.log + просмотр в «Настройках»
- **Главная**: графики matplotlib (выручка + AI-прогноз, тепловая карта), кнопка «Веб-график»
- **Face ID**: клиент переведён на схему `{photo: base64}` (фикс 422), статус движка, список шаблонов
- Новые экраны: Отчёты, Документы, Роли и права, Мастер установки

### v1.3.1 (21.08.2026)
- Динамические вкладки из /ui-config/my по роли
- ФИО и телефон в посещениях (резолв через /clients/)
- Новые вкладки: Dashboard, Payments, Users, Devices, UI-Config
- Централизованная нормализация API-ответов (_as_list)
- Патч endpoint login (/auth/login вместо /auth/token)
- Авто-чинилка битых .py файлов (обрыв строк)
- Миграция enum-данных в БД (gender, category, status, email)

### v1.3.0 (15.08.2026)
- Добавлена AI-аналитика (churn, risk segments)
- Интеграция DAL для устройств

### v1.2.0 (01.08.2026)
- Модуль бухгалтерии (accounting entries)
- Face ID v1

### v1.1.0 (15.07.2026)
- Ролевая модель
- UI-Config (E51)

### v1.0.0 (01.07.2026)
- Первый релиз
- Клиенты, абонементы, посещения

---

*Дополнение сгенерировано на основе рабочих логов и опыта эксплуатации FitIntel Pro.*

---

# FitIntel Pro — Шпаргалки по ролям
## v1.4.0 | 22.08.2026

---

# 🛡️ Шпаргалка: Суперадминистратор

## Доступные экраны
✅ ВСЕ 18: Главная, Клиенты, Абонементы, Входы/Выходы, Расписание, Тарифы, Платежи, Отчёты, Аналитика, Документы, Устройства, Пользователи, Роли и права, Face ID, Лицензия, Настройки, Экраны ролей, Мастер установки

## Ключевые задачи
| Задача | Как сделать |
|--------|-------------|
| Создать пользователя | «Пользователи» → «Создать пользователя» |
| Настроить экраны роли | «Экраны ролей» → роль → чекбоксы → «Сохранить» |
| Матрица прав RBAC | «Роли и права» |
| Проверить лицензию | «Лицензия» — срок, статус, лимиты |
| Подключить устройство | «Устройства» → «Найти устройства» / «Добавить вручную» |
| Провести установку | «Мастер установки» — чек-лист шагов |
| AI-прогноз | «Главная» → график выручки + таблица риска оттока |

## Важно
- ⚠️ «Экраны ролей» нельзя скрыть у себя — защита от самоблокировки
- 🔑 Только вы управляете лицензией и матрицей экранов
- 💾 Регулярный бэкап БД (pg_dump)

## Интерфейс
- Меню «Вид» — тёмная/светлая тема; `Ctrl +` / `Ctrl -` — масштаб
- Кнопка «Обновить» на каждой вкладке — перезагрузка данных


---

# 👔 Шпаргалка: Администратор

## Доступные экраны
✅ Главная, Клиенты, Абонементы, Входы/Выходы, Расписание, Тарифы, Платежи, Отчёты, Аналитика, Документы, Устройства, Пользователи, Роли и права, Face ID, Настройки
❌ Лицензия, Экраны ролей, Мастер установки (только superadmin)

## Ключевые задачи
| Задача | Как сделать |
|--------|-------------|
| Добавить клиента | «Клиенты» → «＋ Добавить» |
| Изменить/удалить клиента | «Клиенты» → двойной клик или «✎ Изменить» / «🗑 Удалить» |
| Продать абонемент | «Абонементы» → «＋ Продать абонемент» |
| Заморозить абонемент | «Абонементы» → «❄ Заморозить» (дата + причина) |
| Провести платёж | «Платежи» → выбрать клиента → «＋ Провести платёж» |
| Возврат/отмена платежа | «Платежи» → выделить платёж → «↩ Возврат» / «✕ Отмена» |
| Выгрузить платежи | «Платежи» → «⇩ Экспорт CSV» |
| Создать тариф | «Тарифы» → «Создать тариф» |
| Сгенерировать договор | «Документы» → «Сгенерировать» |
| Создать пользователя | «Пользователи» → «Создать пользователя» |

## Важно
- 📊 «Главная»: красные строки в таблице оттока — позвонить клиенту
- 🔄 Данные не обновились — кнопка «Обновить» на вкладке
- 🚨 Ошибки смотрите в «Настройки → Логи»

## Интерфейс
- Меню «Вид» — тема; `Ctrl +` / `Ctrl -` — масштаб


---

# 📊 Шпаргалка: Менеджер

## Доступные экраны
✅ Главная, Клиенты, Абонементы, Входы/Выходы, Расписание, Тарифы, Платежи, Отчёты, Аналитика, Документы, Настройки
❌ Пользователи, Устройства, Роли и права, Лицензия, Экраны ролей, Мастер установки

## Ключевые задачи
| Задача | Как сделать |
|--------|-------------|
| Продать абонемент | «Абонементы» → «＋ Продать абонемент» → клиент + тариф |
| Принять оплату | «Платежи» → клиент → «＋ Провести платёж» → «✓ Подтвердить» |
| Оформить возврат | «Платежи» → выделить → «↩ Возврат» (причина обязательна) |
| Отменить ошибочный платёж | «Платежи» → выделить → «✕ Отмена платежа» |
| Выгрузка для бухгалтерии | «Платежи» → «⇩ Экспорт CSV» |
| Проверить риск оттока | «Главная» → красные строки таблицы AI |
| График выручки и прогноз | «Главная» → график; «Веб-график» — в браузере |

## Важно
- 💰 «Отмена» платежа = возврат полной суммы — в отчётах отличайте по причине «Отмена платежа»
- 📈 Прогноз выручки на неделю помогает планировать акции
- 🔍 Поиск клиента — по ФИО и телефону

## Интерфейс
- Меню «Вид» — тема; `Ctrl +` / `Ctrl -` — масштаб


---

# 💪 Шпаргалка: Тренер

## Доступные экраны
✅ Клиенты (только свои), Входы/Выходы, Расписание, Настройки
⚠️ Главная (ограниченно)
❌ Абонементы, Платежи, Пользователи, Устройства, Face ID, Лицензия и админ-экраны

## Ключевые задачи
| Задача | Как сделать |
|--------|-------------|
| Моё расписание | «Расписание» |
| Мои клиенты | «Клиенты» — список уже отфильтрован по вам |
| Посещаемость клиента | «Входы/Выходы» — поиск по ФИО |

## Важно
- 👥 Вы видите только закреплённых за вами клиентов
- 📅 Большой перерыв у клиента — позвоните ему
- 📝 Абонемент оформляют менеджер/администратор

## Интерфейс
- Меню «Вид» — тема; `Ctrl +` / `Ctrl -` — масштаб


---

# 🏠 Шпаргалка: Ресепшен

## Доступные экраны
✅ Клиенты (просмотр), Входы/Выходы, Face ID, Настройки
❌ Все остальные

## Ключевые задачи
| Задача | Как сделать |
|--------|-------------|
| Зарегистрировать вход | «Входы/Выходы» → «Ручной вход» → клиент, способ, зона |
| Найти клиента | «Клиенты» → поиск по ФИО/телефону |
| Проверить Face ID | «Face ID» → «Движок Face ID» (статус) |

## Важно
- 🎯 Face ID на турникете работает автоматически
- ⚠️ Лицо не распозналось — регистрируйте вручную через «Входы/Выходы»
- 📞 При сомнениях сверяйте по телефону в «Клиентах»

## Интерфейс
- Меню «Вид» — тема; `Ctrl +` / `Ctrl -` — масштаб
