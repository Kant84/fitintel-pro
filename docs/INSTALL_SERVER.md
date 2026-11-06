# FitIntel Pro — установка и эксплуатация сервера (ГЛАВНЫЙ ДОКУМЕНТ)

**Версия:** 1.6.2 · **Дата:** 06.11.2026 · **Актуальна для:** `main` с production-установщиком `deploy/install_prod.sh`

Это главное руководство по серверу клуба. Всё остальное (касса, СКУД, уведомления, платформа)
— см. `00-INDEX.md`. Формат каждого шага:

> **Объяснение** — зачем и что происходит · **Действие** — что делать · **Команда** — что выполнить ·
> **Ожидание** — как выглядит успех · **Ошибки и исправления** — если пошло не так.

**Соглашения.** Каталог установки — `/opt/fitintel-pro`. Compose-команды даются через alias
(выполните один раз в каждой новой shell-сессии):

```bash
cd /opt/fitintel-pro
COMPOSE="docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml"
```

---

## 0. Общая картина (что мы строим)

**Объяснение.** Сервер клуба — это VM/железка с Ubuntu и Docker. На ней работают контейнеры:
`db` (PostgreSQL 16, данные в volume `postgres_prod`), `redis` (кэш/брокер), `api` (FastAPI, образ
`fitintel:prod`), `celery-worker`/`celery-beat` (фоновые задачи), `nginx` (вход снаружи, порт 80).
Desktop-клиенты идут через nginx по HTTP/JSON. База живёт в Docker-volume и дампах — контейнер
«без памяти», перенос = volume + `.env` (см. раздел 13 — бэкапы и восстановление).

**Схема:**

```
 desktop-клиенты / СКУД / боты ──► nginx:80 ──► api (fitintel:prod) ──► postgres:16
                                                     │
                                                     └──► redis ──► celery-worker/beat
```

---

## 1. Требования и подготовка

### 1.1. Требования

| Параметр | Минимум | Рекомендуется |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 ГБ | 8 ГБ |
| Диск | 40 ГБ SSD | 80 ГБ SSD (бэкапы + логи) |
| ОС | Ubuntu 22.04/24.04 LTS | чистая VM |
| Сеть | IP в ЛВС клуба | статический IP |
| Доступ | root через `sudo` | SSH с ключом |
| Интернет | нужен для пакетов и образов | для офлайн-режима см. раздел 6 |

Открытые порты: `80` (клиенты), `22` (SSH, только доверенная сеть). Боевой HTTPS — по домену
(см. `WEBPUSH_SETUP.md` / платформа); установщик SSL-сертификат не выпускает.

### 1.2. Подготовка системы

**Объяснение.** Обновляем списки пакетов и ставим базовые утилиты, без которых не работают
следующие шаги: `git` (получение кода), `curl` (ключ Docker), `python3` (генерация `.env`),
`ca-certificates` (проверка HTTPS).

**Действие.** Выполнить на сервере.

**Команда:**
```bash
sudo apt update
sudo apt install -y ca-certificates curl git python3
```

**Ожидание.** Команды завершаются без `E: Unable to locate package`.

**Ошибки и исправления:**

| Ошибка | Исправление |
|---|---|
| `Could not get lock /var/lib/dpkg/lock` | Другой процесс управляет пакетами: `ps aux | grep -E 'apt|dpkg'`, дождаться или `sudo kill <pid>` |
| `Unable to locate package git` | Репозитории не настроены: проверить `/etc/apt/sources.list`, повторить `sudo apt update` |

---

## 2. Установка Docker Engine и Compose v2

### 2.1. Ключ и репозиторий Docker

**Объяснение.** Пакеты из официального репозитория Docker новее и надёжнее штатных. Ключ
проверяет подлинность пакетов.

**Команда:**
```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```
Для Debian замените `ubuntu` на `debian` в URL.

### 2.2. Установка пакетов

**Команда:**
```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

### 2.3. Проверка

**Команда:**
```bash
docker --version && docker compose version && python3 --version && git --version
```

**Ожидание.** Выводится 4 версии, например `Docker version 27.x`, `Docker Compose version v2.x`,
`Python 3.12.x`, `git version 2.x`. Если любая команда отсутствует — устранить до продолжения:
установщик `install_prod.sh` выполнит свою preflight-проверку и остановится.

**Ошибки и исправления:**

| Ошибка | Исправление |
|---|---|
| `Docker Compose v2 is required` (позже, в installer) | Не установлен plugin: проверить `docker compose version`; при выводе «docker-compose version 1.x» (старый бинарник) — удалить `docker-compose`, оставить plugin |
| Нет интернета к download.docker.com | Предпроксировать/разрешить хост, либо готовить офлайн-пакет (раздел 6) |

---

## 3. Способ А — получение кода через GitHub (предпочтительный)

### 3.1. Клонирование

**Объяснение.** Репозиторий публичный: токен GitHub не нужен и не должен вставляться в URL.
Клон создаёт `/opt/fitintel-pro` с полной историей git — дальнейшие обновления делаются `git pull`.

**Действие.** Клонировать и перейти на main.

**Команда:**
```bash
sudo git clone https://github.com/Kant84/fitintel-pro.git /opt/fitintel-pro
cd /opt/fitintel-pro
sudo git checkout main
sudo git pull --ff-only
```

**Ожидание.** `Already on 'main'`, дерево загружено.

### 3.2. Проверка кода перед установкой

**Объяснение.** Перед установкой рабочее дерево должно быть чистым, а installer на месте —
это стоп-кран от неполной копии.

**Команда:**
```bash
sudo git -C /opt/fitintel-pro rev-parse --short HEAD
sudo git -C /opt/fitintel-pro status --short
test -f /opt/fitintel-pro/deploy/install_prod.sh && echo "INSTALLER_PRESENT=1"
```

**Ожидание.** `INSTALLER_PRESENT=1`; `git status --short` пуст (нет неожиданных изменений).
Запишите короткий хеш — он понадобится при сравнении с флешкой (способ Б) и при эскалации
в поддержку.

Далее — к разделу 7 (автоустановка).

---

## 4. Способ Б — перенос кода с USB-флешки

**Объяснение.** Когда сервер не может клонировать с GitHub, код переносится флешкой, но
устанавливается через локальный git-клон — так сохраняется проверка версии и будущие
обновления. На флешку кладётся ТОЛЬКО чистый репозиторий: никаких `.env`, дампов, паролей.

### 4.1. Подготовка флешки (на рабочем ПК с интернетом)

**Команда (PowerShell/bash):**
```bash
git clone https://github.com/Kant84/fitintel-pro.git fitintel-pro
cd fitintel-pro
git checkout main && git pull --ff-only
git rev-parse --short HEAD    # записать хеш
```
Скопируйте всю папку `fitintel-pro`, включая скрытый каталог `.git`, в корень флешки.
Делайте новый чистый клон — не используйте рабочую папку разработки.

### 4.2. Монтирование и проверка на сервере

**Команда:**
```bash
lsblk -o NAME,FSTYPE,LABEL,SIZE,MOUNTPOINTS     # найти раздел флешки (пример: /dev/sdb1)
sudo mkdir -p /mnt/fitintel-usb
sudo mount /dev/НАЙДЕННЫЙ_РАЗДЕЛ /mnt/fitintel-usb
ls /mnt/fitintel-usb/fitintel-pro/deploy/install_prod.sh && echo "USB_INSTALLER_PRESENT=1"
```

**Ошибки и исправления:**

| Ошибка | Исправление |
|---|---|
| Не монтируется | Файловая система не поддерживается: `sudo apt install -y exfatprogs` (для exFAT/NTFS: `ntfs-3g`) |
| `USB_INSTALLER_PRESENT` не появляется | На флешке неполная копия — повторить п. 4.1, не копировать рабочее дерево |

### 4.3. Клонирование с флешки и отвязка

**Объяснение.** Не запускайте installer прямо с флешки. Клонируем в `/opt/fitintel-pro` и
назначаем GitHub-адрес для будущих обновлений.

**Команда:**
```bash
sudo git clone /mnt/fitintel-usb/fitintel-pro /opt/fitintel-pro
sudo git -C /opt/fitintel-pro remote set-url origin https://github.com/Kant84/fitintel-pro.git
sudo git -C /opt/fitintel-pro checkout main
sudo umount /mnt/fitintel-usb
```

**Ожидание.** Хеш `rev-parse --short HEAD` совпадает с записанным на ПК.

### 4.4. Контроль секретов

**Команда:**
```bash
sudo find /opt/fitintel-pro -maxdepth 2 -type f \( -name '.env' -o -name '.env.*' \) -print
```

**Ожидание.** Виден только `deploy/env.example` (шаблон). Если найдены настоящие `.env` —
НЕ запускать установку, удалить только эти файлы и разобраться, откуда попали (флешка
предназначалась для чистого кода).

---

## 5. Офлайн-режим (`--offline`) — установка без интернета

**Объяснение.** Если сервер вообще без интернета: Docker и Python должны быть установлены
заранее, а образы готовятся на машине с интернетом в tar-архивы (`docker load` на сервере).
Системные пакеты в bundle не входят.

**Действие (на машине с интернетом, в репозитории):**
```bash
bash deploy/prepare_offline_bundle.sh   # собирает offline-bundle/offline-images/*.tar
```
На флешку: git-клон (п. 4.1) + каталог `offline-bundle/`.

**Действие (на сервере):**
```bash
cd /opt/fitintel-pro   # получен по способу Б
sudo bash deploy/install_prod.sh --offline
```
Путь к архивам меняется переменной `FITINTEL_OFFLINE_DIR`.

**Ошибки и исправления:**

| Ошибка | Исправление |
|---|---|
| `docker load: open ... no such file` | Не скопирован `offline-bundle/` или неверный `FITINTEL_OFFLINE_DIR` |
| `Required command is missing` на офлайн-сервере | Не установлены заранее Docker/Compose/Python3 — вернуться к разделу 2 |

---

## 6. Автоматическая production-установка

### 6.1. Запуск

**Объяснение.** Установщик делает всё за один прогон: проверяет окружение, генерирует
защищённый `deploy/.env` (отдельные `SECRET_KEY` и `POSTGRES_PASSWORD` именно для этого
сервера, `APP_ENV=prod`, debug выключен), собирает образ `fitintel:prod`, поднимает БД,
прогоняет `alembic upgrade head`, сидирует роли/права, регистрирует первого администратора
(интерактивно), запускает сервисы и проверяет health. Существующий `.env` не перезаписывается.

**Действие.** Запустить и следить за выводом.

**Команда:**
```bash
cd /opt/fitintel-pro
sudo bash deploy/install_prod.sh
```

**Ожидание.** В конце — `PRODUCTION_INSTALL_COMPLETED=1` (или аналогичный финальный маркер)
и приглашение ввести логин/пароль администратора (шаг 7). Первая сборка долгая (компиляция
зависимостей) — не прерывать.

**Ошибки и исправления:**

| Ошибка | Причина и исправление |
|---|---|
| `Required command is missing` | Нет Docker/Python3 — раздел 2 |
| `Docker Compose v2 is required` | Нет plugin — `apt install docker-compose-plugin` |
| `Run the production installer with sudo` | Запуск без root: добавить `sudo` |
| `Refusing to overwrite existing file` | Installer защищает `.env`. На новой VM удалить пустышку; на действующем сервере — НЕ удалять, это защита |
| `POSTGRES_PASSWORD is required` | `.env` создан вручную без пароля: на новой VM удалить `.env` и перезапустить installer; он сгенерирует сам |
| `SECRET_KEY is standard...` | В `.env` стандартный/слабый ключ: заменить на `python3 -c 'import secrets;print(secrets.token_urlsafe(32))'` |
| Ошибка миграций | Не прерывать. Посмотреть: `$COMPOSE run --rm api alembic current`; при расхождении — `alembic upgrade head`. НИКОГДА не заменять миграции `create_all`/`bootstrap_db.py` |
| Ошибка регистрации администратора | Установка не завершена — сервер не считается установленным. Проверить ввод (email, пароль ≥ 12 симв., совпадение) и логи installer'а; повторить прогон |

---

## 7. Регистрация первого администратора

**Объяснение.** Стандартных учёток нет — велосипед без пароля. Администратор создаётся во
время установки: логин = действующий email, пароль ≥ 12 символов, ввод скрыт и не попадает
ни в `.env`, ни в историю команд, ни в git.

**Действие.** На запросы `Login (email): / Password: / Confirm password:` ввести данные.
При несовпадении или коротком пароле installer запросит повторно.

**Ожидание.** Сообщение об успешном создании администратора.

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| Не помню логин | Это email из п. 7; если недоступен — создать нового админа: `$COMPOSE run --rm api python scripts/create_admin.py` (интерактивно, без передачи пароля в аргументах) |
| Не помню пароль | Сброс через desktop «Пользователи» (другой админ) или повторный `scripts/create_admin.py`; SSH на сервер — через учётку ОС, это не вход в FitIntel |

---

## 8. Защищённый доступ к каталогу сервера

**Объяснение.** После установки код принадлежит `root:root`, каталог `750`, `deploy` — `700`,
`deploy/.env` — `600`. Работать — только через `sudo -s`. Это защита от случайного удаления
и чтения секретов посторонними процессами.

**Действие.** Использовать шаблон:
```bash
sudo -s
cd /opt/fitintel-pro
# ... работа ...
exit
```

**Дополнительное ужесточение (рекомендуется, применено на стендах test/nfs):**
```bash
sudo bash scripts/secure_install.sh    # права 750/640/600, группа admin.platform, проверка членов docker
```
**Ожидание:** `SECURE_OK=1`.

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| `Permission denied` при работе с каталогом | Ожидаемо: только `sudo`. Не применять `chmod 777` — это ломает модель безопасности |
| Нет доступа к `deploy/.env` у вашего пользователя | Так задумано; чтение только root. Не копируйте секреты в домашние каталоги |

---

## 9. Проверка установки

### 9.1. Контейнеры

**Команда:**
```bash
$COMPOSE ps
```

**Ожидание.** `db` — healthy, `api`, `nginx`, `celery-worker` (и `celery-beat`, если используется) — Up.

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| `api` — restarting/unhealthy | Логи: `$COMPOSE logs --tail=200 api`. Частые причины: не применены миграции (`$COMPOSE run --rm api alembic upgrade head`), занят порт, неверный `.env` |
| `db` — unhealthy | `$COMPOSE logs db`; обычно первая инициализация — подождать 30–60 с и повторить `ps` |

### 9.2. Health API

**Объяснение.** Проверка изнутри контейнера — не требует открытых наружу портов.

**Команда:**
```bash
$COMPOSE exec -T api python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health/').read().decode())"
```

**Ожидание.** `{"status":"ok","app":"FitIntel Pro","module":"crm","database":"ok"}`

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| 502/000 снаружи сразу после `up -d` | **Норма прогрева:** db healthcheck ~25 с, первые запросы тяжёлые. Подождать 20–30 с и повторить. Не перезапускать по кругу |
| 404 на `/health` | Путь с суффиксом: `/api/v1/health/` (со слэшем) |
| `{"database":"error"}` | БД не готова: `$COMPOSE ps` (db healthy?), затем логи db/api |

### 9.3. Логи

**Команда:**
```bash
$COMPOSE logs --tail=200 api
```

**Ожидание.** Стартовые блоки роутеров, `Application startup complete`, нет traceback.

⚠️ Не публикуйте логи снаружи, если в них персональные данные или credentials.

---

## 10. Лицензия и первый вход

**Объяснение.** Лицензия — одноразовый ключ `FIPRO-…` (Ed25519), привязка к machine-id сервера.
Активация через окно активации desktop или экран «Лицензия». Приватный ключ подписи остаётся
на платформе; на сервере клуба — только публичный ключ проверки. `LICENSE_SECRET` не нужен.

**Действие.**
1. Получить ключ клуба через администратора платформы.
2. Открыть desktop → окно «Активация лицензии» (при первом запуске открывается само) → вставить ключ.
3. В ответе активации система покажет **логин/пароль SuperAdmin из лицензии** — записать в менеджер паролей.
4. Войти; при первом входе — принудительная смена пароля.

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| «Ключ должен начинаться с FIPRO-» | Копировать целиком (Ctrl+A → Ctrl+C в письме, Ctrl+V в окне) |
| «Сервер отклонил: 403» | Ключ уже привязан к другому machine-id → запросить новый ключ у платформы (бесплатно при замене сервера) |
| Перенос на новое железо | Новый machine-id → новый ключ по заявке. Данные переносятся бэкапом (раздел 13), лицензия — новым ключом |

---

## 11. Подключение Windows desktop

**Объяснение.** Desktop — тонкий клиент: хранит только адрес сервера и локальные настройки.
Все данные — на сервере.

**Действие.** Установить `FitIntelDesktop-Setup_v1.6.2.exe` (проверить SHA256 по `RELEASES.md`)
или использовать portable-вариант. При первом запуске ввести адрес сервера:
`http://<IP-сервера>` (окончание `/api/v1` добавится само). Либо прописать в
`fitintel-desktop/client_settings.json`:
```json
{"api_base": "http://<IP-сервера>/api/v1"}
```

**Команда (проверка с Windows):**
```powershell
curl.exe http://<IP-сервера>/api/v1/health/
```

**Ожидание.** JSON `{"status":"ok",...}`. Desktop входит логином/паролем администратора из раздела 7.

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| «Сервер недоступен» в desktop | `ping <IP>`; проверить `api_base`; `curl.exe` выше; файрвол/порт 80 |
| Ошибка сертификата (если HTTPS) | `-k` только для диагностики; для боя — доверенный сертификат (WEBPUSH_SETUP.md) |

---

## 12. Резервное копирование (обязательно сразу после установки!)

### 12.1. Автоматический полный бэкап

**Объяснение.** Полный архив клуба — это не только PostgreSQL, но и SQLite-учётка, файлы/медиа,
лицензия, `deploy/.env`, сертификаты. Установщик его НЕ настраивает — делается одной командой
после установки. Проверен на стендах (restore-test пройден 05.11: счётчики clients/visits/payments
совпали с продом).

**Действие.** Установить таймер:
```bash
sudo bash /opt/fitintel-pro/deploy/backup/install_cron.sh
```

**Проверка:**
```bash
systemctl list-timers fitintel-backup.timer --no-pager
sudo systemctl start fitintel-backup.service
sudo systemctl status fitintel-backup.service --no-pager | head -8
ls -la /opt/fitintel-pro/deploy/backups/ | head
```

**Ожидание.** Таймер ежедневно ~21:30 (+ запуск после перезагрузки VM); архивы
`fitintel_full_*.tar.gz`, права `0600`, ротация 14 дней.

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| Сервис падает | Журнал: `journalctl -u fitintel-backup.service -n 50`; типично — мало места (`df -h`) или права на каталог бэкапов |
| Архив 0 байт | Проверить лог сервиса; убедиться, что postgres-контейнер запущен (`$COMPOSE ps db`) |

### 12.2. Копия вне сервера (второй носитель)

**Объяснение.** Бэкап на том же диске не спасает при гибели VM. Настройте вынос копии —
например, cron 21:45 на nfs → scp на машину 125 (`/etc/cron.d/fitintel-offsite`, ротация 7)
по образцу из ROADMAP E4 (внедрён 05.11, `OFFSITE_TEST_OK=1`).

### 12.3. Восстановление (регламент)

**Объяснение.** Бэкап, который не восстанавливается, — не бэкап. Раз в месяц поднимайте
последний архив на отдельном стенде и сверяйте счётчики.

**Команды (развёртывание архива в отдельную БД на стенде):**
```bash
# распаковать архив, затем:
zcat backups/fitintel_full_ДАТА.tar.gz | tar -x -C /tmp/restore   # структура смотреть в INSTALL и логе сервиса
# PostgreSQL из состава архива → одноразовый контейнер/БД → сверка:
docker exec -i deploy-db-1 psql -U fitnexus_user -d restore_db -c \
  "SELECT (SELECT COUNT(*) FROM clients) AS clients, (SELECT COUNT(*) FROM visits) AS visits, (SELECT COUNT(*) FROM payments) AS payments;"
```

**Ожидание.** Числа совпадают с боевой БД на момент архива (подписки — снимок на момент архива).

---

## 13. Обновление сервера

### 13.1. Штатное обновление (код)

**Объяснение.** Обновление = новый код + пересборка образа + миграции. Поверх действующего
клуба installer повторно не запускается — только штатный цикл.

**Действие.**
```bash
sudo git -C /opt/fitintel-pro pull --ff-only
sudo docker build -t fitintel:prod /opt/fitintel-pro
$COMPOSE run --rm api alembic upgrade head
$COMPOSE up -d
# проверка — раздел 9 (помните про прогрев: sleep 20 перед health)
sleep 20
$COMPOSE exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health/').status)"
```

**Ожидание.** `200` на health; контейнеры Up.

**Ошибки и исправления:**

| Симптом | Исправление |
|---|---|
| `pull --ff-only` отказал | Расхождение истории: `git status`, `git stash` (если локальные правки нужны) или `git reset --hard origin/main` (если нет), затем повторить |
| Образ собрался, api падает | Миграции: `$COMPOSE run --rm api alembic upgrade head`; логи api |
| 502 после up | Прогрев, раздел 9.2 — подождать и повторить |

### 13.2. Поставка образа через tar (клубы без сборки)

**Объяснение.** На узле сборки (test) образ сохраняется в tar и переносится на клубы `docker load`.

**Команды:**
```bash
# узел сборки:
docker save fitintel:prod | gzip > fitintel-prod_v1.6.2.tar.gz
# клуб:
gunzip -c fitintel-prod_v1.6.2.tar.gz | sudo docker load
$COMPOSE up -d
```

### 13.3. «Горячая» правка кода без пересборки (только dev/test!)

**Объяснение.** Если в compose-файле контейнера `api` есть bind-mount кода (`./:/app` или том
на исходники), правки Python подхватываются пересозданием контейнера за секунды — образ
пересобирать не нужно. Проверить наличие bind-mount:

**Команда:**
```bash
grep -A10 "^  api:" ~/fitintel-pro/deploy/docker-compose.test.yml | grep -E "volumes|/app|build"
```

Если томов нет (prod-контур) — способ не работает, только пересборка (13.1–13.2).

---

## 14. Полезные команды (шпаргалка)

```bash
cd /opt/fitintel-pro
COMPOSE="docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml"

$COMPOSE ps                                # состояние
$COMPOSE logs --tail=200 api               # логи api
$COMPOSE restart api                       # перезапуск api
$COMPOSE exec -T db psql -U fitnexus_user -d fitnexus_ai -c "\dt"    # список таблиц
$COMPOSE run --rm api alembic upgrade head # миграции
$COMPOSE run --rm api alembic current      # текущая версия БД
docker exec deploy-api-1 grep -c "метод" /app/app/.../файл.py        # проверка приехавшего фикса
df -h && docker system df                  # место на диске
```

⚠️ Никогда не публикуйте вывод `env`, `printenv`, `docker inspect` и содержимое `deploy/.env` —
там секреты.

---

## 15. Безопасность: секреты и ротация

1. `.env` и `deploy/.env` не попадают в Git и на общую флешку.
2. Каждый клуб — свои `SECRET_KEY`/`POSTGRES_PASSWORD`; одинаковые пароли на всех серверах запрещены.
3. SMTP/SMS/платёжные ключи выдаёт соответствующий сервис — installer их не генерирует.
4. **ITC Basic-auth (турникеты):** логин/пароль хранятся в `deploy/.env` (`ITC_BASIC_USER`/
   `ITC_BASIC_PASSWORD`), доходят до контейнера api; дублируются в реестре ITCService и
   `/etc/fitintel/bridge.env` (ent_bridge). Ротация — одним блоком по всем трём точкам
   (см. SKUD_SETUP.md / ITCService_SETUP.md §«Безопасность»; выполнена 05–06.11.2026).
5. Grafana/Prometheus — только внутренняя сеть/VPN; пароль Grafana сменить сразу (`GF_SECURITY_ADMIN_PASSWORD`).
6. Перед боевым вводом — ротация всех секретов, которые когда-либо попадали в git-историю.

---

## 16. Типовые проблемы (симптом → диагностика → исправление)

| # | Симптом | Диагностика (команда) | Исправление |
|---|---|---|---|
| 1 | `Required command is missing` (installer) | `docker --version; python3 --version` | Раздел 2 — доустановить |
| 2 | `Refusing to overwrite existing file` | `ls -la deploy/.env` | Новая VM — удалить пустышку; действующий сервер — НЕ трогать `.env` |
| 3 | 502 сразу после `up -d` | `sleep 20; curl -s localhost/api/v1/health/` | Прогрев — повторить запрос; не рестартить по кругу |
| 4 | api restarting | `$COMPOSE logs --tail=100 api` | Миграции `alembic upgrade head`; проверить `.env` |
| 5 | «role does not exist» в psql | `\l` внутри db | Пользователь — `fitnexus_user` (см. `POSTGRES_USER` в compose), не `postgres` |
| 6 | pg_dump пустой/ошибка | `pg_dump -h 127.0.0.1 -U fitnexus_user …` | Указать хост/пользователя; fallback — каталог-дамп |
| 7 | Место на диске | `df -h; docker system df` | Ротация `deploy/backups` (14 дн), `docker system prune`; алерт DiskSpaceLow в мониторинге |
| 8 | HTTP 423 | — | Аккаунт заблокирован (5 попыток): подождать 5 мин или сбросить пароль админу |
| 9 | 429 от nginx | лог nginx | Rate-limit (API 10 r/s, auth 5/мин); при законной нагрузке — LAN-whitelist в nginx.conf |
| 10 | Алерты не приходят | `deploy/monitoring/alertmanager/` | receiver сейчас «null» — настроить email/webhook |
| 11 | Медленные face/отчёты (10–60 с) | метрики | BLAS-лимиты в compose: `OPENBLAS/OMP/MKL_NUM_THREADS=1` |
| 12 | 401 на `/skud/*` после ротации | `curl -u itc:НОВЫЙ …/skud/checkaccess` | Одна из трёх точек не обновлена (раздел 15, п. 4) |
| 13 | Desktop «Сервер недоступен» | `ping IP; curl http://IP/api/v1/health/` | Сеть / `api_base` / порт 80 |
| 14 | «Вечный круг» смены пароля superadmin | desktop | Пройти смену до конца; флаг `is_first_login` сбрасывается вместе с license_state (не баг) |

---

## 17. Контрольный чек-лист установки

- [ ] Установлен ожидаемый commit `main` (хеш записан)
- [ ] `deploy/.env` создан именно на этом сервере, права `0600`, стандартных секретов нет
- [ ] `alembic upgrade head` завершился успешно
- [ ] Первый администратор создан через скрытую регистрацию (пароль — в менеджер паролей)
- [ ] `db`, `redis`, `api`, `nginx`, `celery-worker` работают; health — `{"status":"ok",...}`
- [ ] Desktop подключён, вход администратора выполнен, лицензия активна
- [ ] Каталог защищён (`750/700/600`, при желании `secure_install.sh` → `SECURE_OK=1`)
- [ ] **install_cron.sh выполнен** (полный бэкап), пробный архив создан
- [ ] Настроена копия архива вне сервера (второй носитель)
- [ ] Restore-test пройден на отдельном стенде (счётчики совпали)
- [ ] Настроен мониторинг (стек `deploy/monitoring`), пароль Grafana сменён
- [ ] ITC/СКУД-пароль прописан везде по регламенту (три точки)

---

*Документ является главным по серверу FitIntel Pro. Правки — только через репозиторий
(Windows → commit → push), актуализация при каждом релизе.*
