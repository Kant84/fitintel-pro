# FitIntel Pro

**ERP/CRM-система управления фитнес-клубом** — полный цикл от регистрации клиентов и продажи абонементов до контроля доступа (СКУД), кассы (54-ФЗ), AI-аналитики и музыкального пульта.

**Версия:** 1.6.1 | **Статус:** Production Ready | **Лицензия:** Проприетарная

---

## Что это

FitIntel Pro — комплексная система для автоматизации фитнес-клуба. Включает:

- **CRM:** клиенты, абонементы, тарифы, история взаимодействия
- **Касса (54-ФЗ):** смены, фискальные чеки, АТОЛ/Штрих-М, ОФД
- **Платежи:** наличные, карта, СБП, ЮKassa, рекуррентные
- **СКУД:** турникеты (ЭРА, X1), RFID-карты, QR, Face ID, шкафчики (Kerong)
- **Бухгалтерия:** проводки, ПКО/РКО, ОСВ, P&L, баланс, 1С
- **AI-аналитика:** отток клиентов, прогнозы, тепловая карта зала
- **Коммуникации:** MAX-бот, Telegram-бот, Email/SMS/WebPush
- **Музыка/DJ:** плеер mpv, деки A/B, кроссфейд, эквалайзер, пады
- **Маркетинг:** кампании, сегменты, рефералка, геймификация
- **Документы:** шаблоны, генерация PDF/DOCX, подпись
- **Онлайн-запись:** публичный виджет, мини-приложение MAX

---

## Состав системы

| Компонент | Технологии | Где |
|---|---|---|
| **Сервер API** | Python 3.11, FastAPI, SQLAlchemy, PostgreSQL 16, Redis 7, Celery | `app/` |
| **Desktop-клиент** | Python 3.11, PyQt6 (17 вкладок sidebar, ~99 экранов расчётно) | `fitintel-desktop/` |
| **DJ-агент** | Python + mpv (3 процесса: A, B, PAD) | `scripts/music/` |
| **React-админка** | React 18 + Vite + Tailwind (опционально) | `app/src/` |
| **PWA для тренеров** | Отдельный веб-интерфейс | `app/static/trainer-pwa/` |
| **Мониторинг** | Prometheus + Grafana + Loki + Alertmanager | `deploy/monitoring/` |
| **Развёртывание** | Docker Compose (test/prod/dev) | `deploy/` |

---

## Быстрый старт

### Для разработки (Docker)

```bash
# 1. Клонировать
git clone https://github.com/Kant84/fitintel-pro.git
cd fitintel-pro

# 2. Запустить весь стек
cd deploy
docker compose -f docker-compose.test.yml up -d --build

# API: http://localhost:8001/docs
# Проверка: curl http://localhost/api/v1/health/

# 3. Desktop
cd ../fitintel-desktop
python main.py
```

Первая сборка — 10–30 минут (компилируется `dlib`).

### Для продакшена

```bash
# 1. Загрузить образ
docker load -i fitintel-prod_v1.6.1.tar.gz

# 2. Настроить .env
cd deploy
cp env.example .env
nano .env    # POSTGRES_PASSWORD, SECRET_KEY

# 3. Запустить
docker compose -f docker-compose.prod.yml up -d

# 4. Инициализация БД
docker compose -f docker-compose.prod.yml exec api python -m scripts.bootstrap_db
docker compose -f docker-compose.prod.yml exec api python -m app.db.seed.run_seed

# 5. Создать администратора
docker compose -f docker-compose.prod.yml exec \
  -e SEED_ADMIN_EMAIL="admin@club.ru" \
  -e SEED_ADMIN_USERNAME="admin" \
  -e SEED_ADMIN_PASSWORD="СложныйПароль123" \
  api python -m app.db.seed.seed_admin
```

### Desktop-клиент

```powershell
# Установщик
# Запустите FitIntelDesktop-Setup_v1.6.1.exe (~154 МБ)
# Мастер установки спросит адрес сервера

# Или из исходников
cd fitintel-desktop
python -m venv .venv-desktop
.\.venv-desktop\Scripts\Activate.ps1
pip install -r requirements-desktop.txt
python main.py
```

---

## Документация

### Основные документы

| Документ | Для кого | Содержание |
|---|---|---|
| **[Техническая документация](docs/ТЕХНИЧЕСКАЯ_ДОКУМЕНТАЦИЯ.md)** | разработчики, DevOps | Архитектура, стек, структура, зависимости, модели данных, ~191+ API, RBAC, HAL, сервисы, музыка, инфраструктура, команды, безопасность, интеграции, мониторинг, troubleshooting |
| **[Инструкция пользователя](docs/ИНСТРУКЦИЯ_ПОЛЬЗОВАТЕЛЯ.md)** | сотрудники клуба | Начало работы, экраны по ролям, 17 вкладок пошагово, сценарии, FAQ, поддержка |
| **[README](README.md)** | все | Этот файл — навигация по проекту |

### Дополнительные документы

| Документ | Для кого | Содержание |
|---|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | разработчики | Компоненты, адаптеры, потоки данных, БД, RBAC, deploy-топология |
| [API_OVERVIEW.md](docs/API_OVERVIEW.md) | разработчики, 1С-интеграторы | Все группы эндпоинтов, коды ошибок, примеры |
| [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | администратор клуба | Мастер установки, роли/права/экраны, бэкапы, адаптеры, feature flags |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | сотрудники клуба | Сценарии по ролям: касса, абонементы, доступ, тренеры, чаты |
| [DESKTOP_GUIDE.md](docs/DESKTOP_GUIDE.md) | сотрудники + админ | Полная инструкция по desktop (v1.5.3), каждая кнопка |
| [FISCAL_GUIDE.md](docs/FISCAL_GUIDE.md) | кассир, бухгалтер | Смены, авто-фискализация, проводки, эквайринг, онлайн, реготчётность |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | все | Симптом → причина → решение, логи, диагностика |
| [INSTALL_SERVER.md](docs/INSTALL_SERVER.md) | DevOps | Установка сервера на Ubuntu с нуля |
| [RBAC.md](docs/RBAC.md) | администратор | Полное описание ролей и прав (модель) |
| [RBAC (2).md](docs/RBAC%20(2).md) | администратор | Реальный дамп прав из БД (05.10.2026) |
| [SPECIFICATION.md](docs/SPECIFICATION.md) | заказчик, менеджер | Технические характеристики, функционал, условия поставки |
| [EMAIL_SETUP_GUIDE.md](docs/EMAIL_SETUP_GUIDE.md) | администратор | Настройка почты (2 профиля SMTP, очередь, диагностика) |
| [docs_MAX_bot_shop.md](docs/docs_MAX_bot_shop.md) | администратор | MAX-бот + Магазин (склад/киоск, пополнение баланса) |
| [Docs_MAX_miniapp_YooKassa.md](docs/Docs_MAX_miniapp_YooKassa.md) | администратор | Мини-приложение MAX + ЮKassa (webhook, бонусы) |
| [INSTRUCTION_RFID.md](docs/INSTRUCTION_RFID.md) | ресепшен | RFID: браслеты, карты, замки Kerong S80F |
| [ITCService_SETUP.md](docs/ITCService_SETUP.md) | DevOps | Настройка ITCService (СКУД ITC) |
| [ITCService_CONFIG.md](docs/ITCService_CONFIG.md) | DevOps | Реестр ITCService (готовый .reg) |
| [KERONG_KR-S80_SETUP.md](docs/KERONG_KR-S80_SETUP.md) | DevOps | Настройка замка Kerong KR-S80 |
| [FitIntel_Pro_Полная_документация.md](docs/FitIntel_Pro_Полная_документация.md) | все | Полная документация v1.4.0 |
| [FitIntel_Pro_Расширенное_руководство.md](docs/FitIntel_Pro_Расширенное_руководство.md) | все | Расширенное руководство v1.4.0 |
| [FitIntel_Pro_Шпаргалки_по_ролям.md](docs/FitIntel_Pro_Шпаргалки_по_ролям.md) | сотрудники | Шпаргалки: superadmin, admin, manager, trainer, reception |
| [FitIntel_Pro_Presentation.html](docs/FitIntel_Pro_Presentation.html) | презентация | Презентация для клиента |
| [FitIntel_Pro_Technical_Documentation_v1.1.pdf](docs/FitIntel_Pro_Technical_Documentation_v1.1.pdf) | заказчик | PDF для печати |
| [v1.2.0_changelog.html](docs/v1.2.0_changelog.html) | все | Changelog v1.2.0 |
| [RELEASES.md](RELEASES.md) | все | Релизы + SHA256 |
| [PROD_NOTES.md](PROD_NOTES.md) | DevOps | Что важно перед продом (E1–E58) |
---

## Структура репозитория

```
fitintel-pro/
├── app/                         # Backend (FastAPI)
│   ├── api/v1/                  # ~90 роутеров
│   ├── core/                    # config, security, license
│   ├── db/                      # session, seed
│   ├── models/                  # ~50 SQLAlchemy моделей
│   ├── repositories/            # ~22 репозитория
│   ├── schemas/                 # Pydantic-схемы
│   ├── services/                # ~55 сервисов + подпакеты
│   ├── hardware/                # HAL (драйверы устройств)
│   ├── integrations/            # MAX, email, sms, telegram, 1c
│   ├── ml/                      # AI-модели
│   ├── tasks/                   # Celery-задачи
│   ├── static/trainer-pwa/      # PWA для тренеров
│   ├── src/                     # React-админка (опционально)
│   └── main.py                  # Точка входа
│
├── fitintel-desktop/            # Desktop (PyQt6)
│   ├── api/client.py            # HTTP-клиент
│   ├── windows/                 # 17 вкладок + 11 окон
│   ├── rfid/                    # RFID-операции
│   ├── assets/                  # Иконки
│   ├── main.py
│   ├── FitIntelDesktop.spec     # PyInstaller
│   └── installer.iss            # Inno Setup
│
├── scripts/                     # DJ-агент, бэкапы, seed
│   ├── music/                   # agent, deck, pads, duck, skud_trigger
│   └── backup/                  # backup.ps1, restore.ps1, install_cron.sh
│
├── deploy/                      # Развёртывание
│   ├── docker-compose.test.yml
│   ├── docker-compose.prod.yml
│   ├── docker-compose.dev.yml
│   ├── env.example
│   ├── nginx/
│   ├── monitoring/              # Prometheus, Grafana, Loki, Alertmanager
│   ├── ansible/, systemd/, terraform/
│   └── backup/
│
├── mpv/                         # mpv.exe (~120 МБ, не в git)
├── tools/                       # nssm.exe (не в git)
├── docs/                        # Документация
├── requirements-base.txt        # Тяжёлые (dlib, ML, RFID)
├── requirements.txt             # Сервер API
├── requirements-dev.txt         # Разработка
├── README.md                    # Этот файл
└── RELEASES.md                  # Релизы + SHA256
```

---

## Требования

### Сервер

| Параметр | Минимум | Рекомендуется |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 ГБ | 8 ГБ |
| Диск | 40 ГБ SSD | 80 ГБ SSD |
| ОС | Ubuntu 20.04+/22.04 LTS | Ubuntu 22.04 LTS |
| Docker | Engine 24+ + Compose plugin | То же + fail2ban, NTP |
| Порты | 80, 22 | + 443, 9090, 3000 (только внутри) |

### Desktop-клиент

| Параметр | Значение |
|---|---|
| ОС | Windows 10/11 x64 |
| RAM | 4 ГБ |
| Диск | 500 МБ |
| Разрешение | от 1280×800 |
| Сеть | Доступ до сервера по TCP 8001 (или 80/443) |
| Периферия (опц.) | Веб-камера (Face ID), USB-считыватель RFID, принтер |

---

## Ключевые возможности

### CRM и продажи
- Карточки клиентов, история взаимодействия (timeline)
- Абонементы: продажа, заморозка, продление, отмена
- Тарифы: лимитированные, безлимитные, дневные/ночные
- Расписание: занятия, тренеры, записи
- Услуги: каталог, категории, вместимость

### Касса (54-ФЗ)
- Кассовые смены (нал/безнал раздельно)
- Авто-фискализация при подтверждении платежа
- АТОЛ ДТО 10, Штрих-М, Эвотор, Меркурий
- X/Z-отчёты, снятие кассы (инкассация)
- Настройка ККТ через UI

### Платежи и онлайн
- Наличные, карта, СБП, перевод, онлайн, кошелёк
- ЮKassa (webhook HMAC, идемпотентность, автосписания)
- Рекуррентные платежи
- Сбер, Тинькофф, Райффайзен (адаптеры)

### Доступ в клуб (СКУД)
- RFID-карты, браслеты (Mifare)
- QR-коды (статич. + динамич. HMAC)
- Face ID (dlib, ResNet-34)
- Турникеты ЭРА, X1
- 6 драйверов СКУД + 1 RFID-ридер (7 файлов в `app/hardware/drivers/`)
- Замки Kerong (offline + online: TTLock, KERONG Cloud)
- Шкафчики, anti-passback, графики доступа

### Коммуникации
- MAX-бот (FSM, сценарии, рассылки)
- Telegram-бот
- Email (SMTP + очередь, 2 профиля)
- SMS (smsc.ru)
- Web Push (VAPID)

### AI и аналитика
- Дашборд (KPI, прогнозы)
- Модель оттока клиентов (scikit-learn)
- Тепловая карта зала
- Прогноз выручки/посещаемости
- Рекомендации цен (self-learning)

### Музыка/DJ
- Плеер mpv (3 процесса: A, B, PAD)
- Кроссфейд (0–30 сек)
- Эквалайзер (бас/середина/верха)
- Пады (one-shot поверх музыки)
- Дакинг микрофона (авто-приглушение)
- Авто-микс (папка по кругу, плейлист)
- Лицензия на коммерческую музыку

### Управление
- RBAC: 9 ролей, 51 разрешение
- Строгая модель экранов (ui_config)
- Аудит действий с retention
- Feature flags (процентные раскатки)
- Лицензия Ed25519
- White-label, мультитенантность

---

## Технологический стек

### Backend
- **FastAPI** 0.137.1 — ASGI веб-фреймворк
- **SQLAlchemy** 2.0.51 — ORM
- **PostgreSQL** 16 — БД
- **Redis** 7 — кэш, брокер
- **Celery** 5.6.3 — фоновые задачи
- **APScheduler** 3.11.2 — планировщик
- **Pydantic** 2.13.4 — валидация
- **PyJWT** 2.13.0 — JWT
- **Alembic** 1.18.4 — миграции

### ML / AI
- **dlib** 20.0.1 + **face_recognition** — Face ID
- **scikit-learn** — модель оттока
- **xgboost**, **pyarrow** — дополнительные ML

### Frontend
- **PyQt6** 6.6+ — desktop
- **React** 18 + **Vite** — админка (опц.)
- **Tailwind CSS** — стили

### Инфраструктура
- **Docker** + **Docker Compose**
- **Nginx** — reverse proxy, TLS, rate-limit
- **Prometheus** + **Grafana** — метрики
- **Loki** + **Promtail** — логи
- **Alertmanager** — алерты
- **mpv** v0.41+ — плеер музыки
- **NSSM** 2.24 — служба Windows

---

## Обновления

### Сервер

```bash
cd ~/fitintel-pro
git pull
cd deploy
docker compose -f docker-compose.test.yml build api
docker compose -f docker-compose.test.yml up -d api

# При изменении моделей:
docker compose -f docker-compose.test.yml exec api alembic upgrade head
```

### Desktop

Запустите новый установщик — поставится поверх.

---

## Команды администрирования

### Docker

```bash
# Статус
docker compose -f docker-compose.test.yml ps

# Логи (без health-спама)
docker compose -f docker-compose.test.yml logs -f api 2>&1 | grep -v health

# Перезапуск
docker compose -f docker-compose.test.yml restart api

# Остановка
docker compose -f docker-compose.test.yml down

# Полный сброс (ВСЕ ДАННЫЕ УДАЛЯТСЯ!)
docker compose -f docker-compose.test.yml down -v
```

### База данных

```bash
# Консоль psql
docker exec -it deploy-db-1 psql -U fitnexus_user -d fitnexus_ai

# Запрос
docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai \
  -c "SELECT id, name, desired_state FROM music_zones;"

# Список таблиц
docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c "\dt"
```

### Проверка

```bash
curl -s http://localhost/api/v1/health/
# {"status":"ok","app":"FitIntel Pro","module":"crm","database":"ok"}
```

### Бэкапы

```bash
# Linux — установить cron
bash ~/fitintel-pro/scripts/backup/install_cron.sh

# Восстановление
gunzip -c db_ДАТА.sql.gz | \
  docker compose -f deploy/docker-compose.test.yml exec -T db \
  psql -U fitnexus_user -d fitnexus_ai
```

### Сборка desktop-установщика

```powershell
cd fitintel-desktop

# 1. PyInstaller
Remove-Item dist -Recurse -Force
Remove-Item build -Recurse -Force
pyinstaller FitIntelDesktop.spec --noconfirm

# 2. Inno Setup
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# 3. Результат
Get-ChildItem installer_out\
# FitIntelDesktop-Setup_v1.6.1.exe
```

---

## Развёртывание в клуб

### Сценарий 1: Сервер в клубе

1. Установить сервер на Ubuntu (7 команд из `INSTALL_SERVER.md`)
2. Установить desktop на каждый ПК (`FitIntelDesktop-Setup_v1.6.1.exe`)
3. В диалоге установки указать `http://192.168.x.x/api/v1`
4. Залогиниться под superadmin
5. Настроить папку музыки (`⚙ Плеер…`)
6. Создать тарифы, услуги, пользователей

### Сценарий 2: Сервер в облаке

1. Развернуть сервер на VPS (Yandex Cloud, Selectel)
2. Настроить домен + SSL (Let's Encrypt)
3. Установить desktop на ПК клуба
4. В диалоге установки указать `https://fit.club.ru/api/v1`
5. Сеть клуба → интернет → сервер

### Сценарий 3: Сеть клубов

1. Развернуть сервер (общий или по клубу)
2. White-label для каждого клуба
3. Мультитенантность через `/commercial/tenants`
4. Единый RBAC для всей сети

---

## Безопасность

- **JWT** HS256, access 30 мин, refresh 7 дней
- **bcrypt** пароли (12 rounds)
- **5 неверных паролей** → блокировка 5 мин
- **HTTPS** TLS 1.2/1.3 (Nginx)
- **Rate limit:** API 10 r/s, auth 5/мин, боты 30/сек
- **152-ФЗ:** анонимизация, право на забвение
- **Face ID:** только self-hosted
- **Лицензия:** Ed25519, привязка к machine-id

**Перед продом:**

1. Сменить ВСЕ пароли по умолчанию
2. Свой `SECRET_KEY` в `.env`
3. Firewall: только 80/443 наружу
4. SSL-сертификаты
5. Регулярные бэкапы
6. Токен GitHub удалить после клонирования

---

## Поддержка

| Канал | Контакт |
|---|---|
| Desktop — кнопка «Помощь» | Меню → Поддержка разработчика (MAX) |
| Email | `support@fixintel.ru` |
| Логи | «Настройки → Логи → Открыть папку» |
| Диагностика | `docker compose logs api` |

**Что приложить к обращению:**

- Версия FitIntel (v1.6.1)
- Скриншот ошибки
- Логи (кнопка «Скопировать логи»)
- Время инцидента
- Описание: что делали → что ожидали → что получили

---

## Лицензия

**Проприетарная.** © 2026 FitIntel

Все права защищены. Передача, копирование или распространение без письменного разрешения запрещены.

---

## Ссылки

- **Репозиторий:** https://github.com/Kant84/fitintel-pro
- **Релизы:** [RELEASES.md](RELEASES.md)
- **Техническая документация:** [docs/ТЕХНИЧЕСКАЯ_ДОКУМЕНТАЦИЯ.md](docs/ТЕХНИЧЕСКАЯ_ДОКУМЕНТАЦИЯ.md)
- **Инструкция пользователя:** [docs/ИНСТРУКЦИЯ_ПОЛЬЗОВАТЕЛЯ.md](docs/ИНСТРУКЦИЯ_ПОЛЬЗОВАТЕЛЯ.md)
- **Поддержка:** support@fixintel.ru

---

**FitIntel Pro v1.6.1** — Production Ready

*Последнее обновление README: Октябрь 2026*
`