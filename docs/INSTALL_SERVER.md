# FitIntel Pro — подробная установка и настройка сервера

Актуально для ветки `main` с production-установщиком из commit `2216b0a1`.

Поддерживаются два способа получения кода:

1. **Через GitHub** — предпочтительный способ при доступном интернете.
2. **С USB-флешки** — код переносится на съёмном носителе, а системные пакеты и Docker-зависимости загружаются через интернет.

> **Важно:** текущий установщик не является полностью автономным offline-установщиком. Команды `docker build` и `docker compose pull` требуют доступа к репозиториям пакетов и образов. Перед массовым внедрением выполните контрольную установку на чистой VM.

Не используйте для production старые инструкции с `docker-compose.test.yml`, `scripts/bootstrap_db.py`, стандартными паролями или паролями в аргументах командной строки.

## Содержание

1. Требования и подготовка
2. Установка Docker и необходимых пакетов
3. Способ А — установка кода через GitHub
4. Способ Б — перенос кода с USB-флешки
5. Автоматическая production-установка
6. Регистрация первого администратора
7. Защищённый доступ к каталогу сервера
8. Проверка установки
9. Лицензия и первый вход
10. Подключение Windows desktop
11. Резервное копирование
12. Обновление сервера
13. Полезные команды
14. Безопасность
15. Решение типовых проблем
16. Контрольный чек-лист

## 1. Требования и подготовка

### Аппаратные и системные требования

- Ubuntu 24.04 LTS; предпочтительна чистая VM или отдельный физический сервер.
- Минимум 2 CPU, 4 GB RAM и 40 GB свободного диска.
- Доступ root через `sudo`.
- Git, Python 3, Docker Engine и Docker Compose v2.
- Доступ в интернет для системных пакетов, Docker Hub и базового Docker-образа.
- Открытые порты 80/443 для клиентских подключений; SSH только для доверенной сети администратора.
- Для боевого HTTPS — сертификат и приватный ключ домена.

Установщик не выпускает доверенный SSL-сертификат и не заменяет настройку домена.

### Стандартный каталог установки

В руководстве используется:

```text
/opt/fitintel-pro
```

Это отдельный системный каталог, а не домашняя папка пользователя. После установки он будет защищён правами Linux.

## 2. Установка Docker и необходимых пакетов

Команды ниже выполняются на сервере Ubuntu независимо от выбранного способа получения кода.

### 2.1. Обновление списка пакетов и установка базовых утилит

```bash
sudo apt update
sudo apt install -y ca-certificates curl git python3
```

- `ca-certificates` — проверка HTTPS-сертификатов.
- `curl` — загрузка ключа репозитория Docker.
- `git` — получение и последующее обновление исходного кода.
- `python3` — генерация защищённого `deploy/.env`.

### 2.2. Добавление официального ключа Docker

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Ключ проверяет подлинность пакетов Docker.

### 2.3. Подключение репозитория Docker

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Для Debian используйте `https://download.docker.com/linux/debian`.

### 2.4. Установка Docker Engine и Compose v2

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

### 2.5. Проверка установки

```bash
docker --version
docker compose version
python3 --version
git --version
```

Если любая команда отсутствует, сначала устраните ошибку. Installer также выполнит собственную preflight-проверку.

## 3. Способ А — установка кода через GitHub

### 3.1. Клонирование репозитория

Репозиторий публичный. Токен GitHub для клонирования не нужен и не должен вставляться в URL.

```bash
sudo git clone https://github.com/Kant84/fitintel-pro.git /opt/fitintel-pro
```

Команда создаёт `/opt/fitintel-pro` и загружает репозиторий с историей Git.

### 3.2. Выбор основной ветки

```bash
cd /opt/fitintel-pro
sudo git checkout main
sudo git pull --ff-only
```

`--ff-only` не создаёт скрытый merge и останавливается при расхождении истории.

### 3.3. Проверка полученного кода

```bash
sudo git -C /opt/fitintel-pro rev-parse --short HEAD
sudo git -C /opt/fitintel-pro status --short
test -f /opt/fitintel-pro/deploy/install_prod.sh && echo "INSTALLER_PRESENT=1"
```

Перед установкой рабочее дерево не должно содержать неожиданных изменений.

Теперь переходите к разделу 5.

## 4. Способ Б — перенос кода с USB-флешки

Этот способ подходит, когда скачать репозиторий непосредственно на сервере нельзя, но сервер может загружать системные пакеты и Docker-зависимости.

> На флешку переносится только чистый репозиторий. Не копируйте туда действующие `.env`, `deploy/.env`, резервные копии, пароли, токены или приватные ключи.

### 4.1. Подготовка репозитория на компьютере с GitHub

Выполните на рабочем компьютере:

```bash
git clone https://github.com/Kant84/fitintel-pro.git fitintel-pro
cd fitintel-pro
git checkout main
git pull --ff-only
git rev-parse --short HEAD
```

Сохраните выведенный короткий hash версии. На сервере он поможет проверить, что перенесён именно тот выпуск.

Скопируйте всю папку `fitintel-pro`, включая скрытый каталог `.git`, в корень флешки. Наличие `.git` позволит проверить версию и настроить последующие обновления через GitHub.

Не используйте папку действующего разработческого репозитория, если в ней есть локальные настройки или секреты. Для переноса делайте новый чистый `git clone`.

### 4.2. Определение флешки на сервере

Подключите флешку к серверу и выполните:

```bash
lsblk -o NAME,FSTYPE,LABEL,SIZE,MOUNTPOINTS
```

Найдите раздел по размеру, файловой системе и метке. Пример имени устройства: `/dev/sdb1`. Это только пример — не подставляйте его без проверки.

### 4.3. Монтирование флешки

Создайте точку монтирования:

```bash
sudo mkdir -p /mnt/fitintel-usb
```

Если Ubuntu уже смонтировала флешку автоматически, используйте существующий путь из `lsblk`. Для ручного монтирования подставьте фактически найденный раздел:

```bash
sudo mount /dev/НАЙДЕННЫЙ_РАЗДЕЛ /mnt/fitintel-usb
```

Проверьте наличие репозитория и installer:

```bash
ls -la /mnt/fitintel-usb/fitintel-pro
test -f /mnt/fitintel-usb/fitintel-pro/deploy/install_prod.sh && \
  echo "USB_INSTALLER_PRESENT=1"
```

Если installer отсутствует, остановитесь: на флешке находится неподходящая или неполная копия.

### 4.4. Клонирование с флешки в системный каталог

Не запускайте installer прямо со съёмного носителя. Создайте локальный Git-клон:

```bash
sudo git clone /mnt/fitintel-usb/fitintel-pro /opt/fitintel-pro
```

Установите постоянный GitHub-адрес для будущих обновлений:

```bash
sudo git -C /opt/fitintel-pro remote set-url origin \
  https://github.com/Kant84/fitintel-pro.git
sudo git -C /opt/fitintel-pro checkout main
```

Пока интернет к GitHub недоступен, не выполняйте `git pull`: локальная копия уже содержит перенесённую версию.

### 4.5. Проверка версии и секретных файлов

```bash
sudo git -C /opt/fitintel-pro rev-parse --short HEAD
sudo git -C /opt/fitintel-pro status --short
```

Сравните hash с версией, записанной при подготовке флешки.

Проверьте, что секретные env-файлы не попали в установочный каталог:

```bash
sudo find /opt/fitintel-pro -maxdepth 2 -type f \
  \( -name '.env' -o -name '.env.*' \) -print
```

Файл `.env.example` является шаблоном и допустим. Настоящие `.env` и `deploy/.env` с прежнего сервера переносить нельзя. Если они обнаружены, не запускайте установку до проверки и удаления только этих ошибочно скопированных файлов.

### 4.6. Отключение флешки

После успешного клонирования:

```bash
sudo umount /mnt/fitintel-usb
```

Если флешка монтировалась автоматически в другой каталог, отключайте её через соответствующий путь или штатный файловый менеджер.

Теперь переходите к разделу 5.

### 4.7. Ограничение полностью автономной установки

Одной флешки с исходным кодом недостаточно для полностью offline-установки. Текущий installer:

- собирает `fitintel:prod` и загружает базовый образ и Python-зависимости;
- выполняет `docker compose pull db redis nginx`;
- не содержит режима `--offline` и не заменяет загрузку командой `docker load`.

Поэтому не отключайте интернет до завершения установки. Для полностью автономного сценария требуется отдельный пакет с предсобранными образами и специальный offline installer; его наличие нельзя предполагать.

## 5. Автоматическая production-установка

Запустите:

```bash
cd /opt/fitintel-pro
sudo bash deploy/install_prod.sh
```

Установщик последовательно:

1. Проверяет root, Docker, Compose и Python 3.
2. Создаёт `deploy/.env`, только если файл ещё не существует.
3. Генерирует отдельные `SECRET_KEY` и `POSTGRES_PASSWORD` для этого сервера.
4. Устанавливает `APP_ENV=prod`, отключает debug и публичную документацию API.
5. Назначает env-файлу права `0600` и проверяет обязательные значения без их вывода.
6. Собирает `fitintel:prod`.
7. Загружает инфраструктурные образы и запускает PostgreSQL/Redis.
8. Ждёт готовности БД и выполняет `alembic upgrade head`.
9. Заполняет роли и права без создания стандартного администратора.
10. Запрашивает данные первого администратора.
11. Запускает production-сервисы и проверяет API health.
12. Назначает каталогу установки владельца `root:root` и защитные права.

Существующий `deploy/.env` не перезаписывается. Не копируйте env-файл с компьютера разработчика или другого клуба.

Первая сборка может занять продолжительное время. Не прерывайте её без необходимости.

## 6. Регистрация первого администратора

Во время установки появятся запросы:

```text
Login (email): ...
Password: ...
Confirm password: ...
```

### Что вводить

- **Login (email)** — действующий email администратора; он используется как логин.
- **Password** — пароль длиной не менее 12 символов; ввод скрыт.
- **Confirm password** — тот же пароль повторно; ввод также скрыт.

При несовпадении или недостаточной длине installer запросит пароль заново.

Пароль:

- не записывается в `deploy/.env`;
- не передаётся значением в аргументах Docker;
- не сохраняется в Git;
- не выводится установщиком в журнал.

Стандартного логина или пароля администратора нет. Ошибка регистрации останавливает установку; такой сервер нельзя считать успешно установленным.

## 7. Защищённый доступ к каталогу сервера

После успешной установки:

- владелец файлов — `root:root`;
- каталог установки имеет права `750`;
- каталог `deploy` имеет права `700`;
- `deploy/.env` имеет права `600`.

Для администрирования используйте:

```bash
sudo -s
cd /opt/fitintel-pro
```

После завершения работы:

```bash
exit
```

Это авторизация Linux, а не вход в FitIntel. `sudo` может временно кэшировать пароль ОС. Не применяйте `chmod 777` и не используйте пароль FitIntel как пароль Linux.

## 8. Проверка установки

### 8.1. Состояние контейнеров

```bash
sudo docker compose \
  --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml ps
```

Проверьте `db`, `redis`, `api`, `nginx` и `celery-worker`.

### 8.2. Health API

```bash
sudo docker compose \
  --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml \
  exec -T api python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health/').read().decode())"
```

Запрос выполняется внутри API-контейнера и не требует публикации дополнительного порта.

### 8.3. Логи

```bash
sudo docker compose \
  --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml \
  logs --tail=200 api
```

Не публикуйте логи, если в них видны персональные данные или credentials.

Сообщение `PRODUCTION_INSTALL_COMPLETED=1` не заменяет проверку всех сервисов, HTTPS, регистрации и входа.

## 9. Лицензия и первый вход

1. Получите подписанную лицензию клуба через admin.platform.
2. Активируйте её штатным окном активации FitIntel.
3. Войдите с email и паролем администратора, созданными при установке.
4. Проверьте срок и лимиты лицензии.

Приватный ключ подписи остаётся у платформы. На сервере клуба используется только публичный ключ проверки. `LICENSE_SECRET` в production `.env` не нужен.

## 10. Подключение Windows desktop

В `fitintel-desktop/client_settings.json` укажите фактический адрес:

```json
{
  "api_base": "https://club.example.com/api/v1"
}
```

Для локальной сети используйте реальный адрес сервера и настроенную схему HTTP/HTTPS. Затем запустите desktop и войдите с созданными учётными данными.

Проверка с Windows:

```powershell
curl.exe -k https://club.example.com/api/v1/health/
```

Параметр `-k` допустим только для диагностики с самоподписанным сертификатом. Для боевой работы используйте доверенный сертификат и не отключайте проверку TLS.

## 11. Резервное копирование

Общий installer пока не настраивает резервное копирование. После установки выполните:

```bash
sudo bash /opt/fitintel-pro/deploy/backup/install_cron.sh
```

Проверка timer и ручного архива:

```bash
systemctl list-timers fitintel-backup.timer --no-pager
sudo systemctl start fitintel-backup.service
sudo systemctl status fitintel-backup.service --no-pager
```

Архивы должны иметь права `0600`. Храните копию вне сервера. Перед боевым вводом выполните восстановление на отдельном стенде: наличие архива само по себе восстановление не доказывает.

## 12. Обновление сервера

### 12.1. Обновление через GitHub

```bash
sudo git -C /opt/fitintel-pro pull --ff-only
```

Если код первоначально переносили с флешки, команда использует GitHub-адрес, настроенный в разделе 4.4.

### 12.2. Обновление с флешки

На компьютере подготовьте новый чистый клон нужной версии. На сервере подключите флешку и добавьте её как временный remote:

```bash
sudo git -C /opt/fitintel-pro remote add usb \
  /mnt/fitintel-usb/fitintel-pro
sudo git -C /opt/fitintel-pro fetch usb main
sudo git -C /opt/fitintel-pro merge --ff-only usb/main
sudo git -C /opt/fitintel-pro remote remove usb
```

Если remote `usb` уже существует, сначала проверьте его адрес командой `sudo git -C /opt/fitintel-pro remote -v`; не перезаписывайте remotes без необходимости.

### 12.3. Пересборка и миграции

```bash
sudo docker build -t fitintel:prod /opt/fitintel-pro

sudo docker compose \
  --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml \
  run --rm api alembic upgrade head

sudo docker compose \
  --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml up -d
```

После обновления повторите раздел 8. Не запускайте installer поверх действующего клуба ради обычного обновления.

## 13. Полезные команды

### Статус сервисов

```bash
sudo docker compose --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml ps
```

### Логи API

```bash
sudo docker compose --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml logs --tail=200 api
```

### Перезапуск API

```bash
sudo docker compose --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml restart api
```

### Миграции

```bash
sudo docker compose --env-file /opt/fitintel-pro/deploy/.env \
  -f /opt/fitintel-pro/deploy/docker-compose.prod.yml \
  run --rm api alembic upgrade head
```

Не используйте `bootstrap_db.py/create_all` вместо Alembic.

Не публикуйте вывод `env`, `printenv`, `docker inspect` или содержимое `deploy/.env`: там могут быть секреты.

## 14. Безопасность

- `.env` и `deploy/.env` не должны попадать в Git или на общую флешку.
- Каждый клуб получает собственные секреты; одинаковые пароли БД и `SECRET_KEY` на всех серверах запрещены.
- Ранее раскрытые credentials необходимо ротировать, а не только удалить из последней версии кода.
- SMTP, SMS, платёжные и другие внешние секреты не генерируются случайно: их выдаёт соответствующий сервис.
- Приватный лицензионный ключ платформы не устанавливается на сервер клуба.
- Grafana/Prometheus не открывайте в интернет; используйте внутреннюю сеть или VPN.
- Не передавайте пароли в `docker compose -e NAME=VALUE`, аргументах `ps`, командной истории или чате.

## 15. Решение типовых проблем

| Симптом | Объяснение и действие |
|---|---|
| `Required command is missing` | Не установлен Docker или Python 3; вернитесь к разделу 2 |
| `Docker Compose v2 is required` | Установите `docker-compose-plugin`; команда должна быть `docker compose`, не старый `docker-compose` |
| `Run the production installer with sudo` | Запустите `sudo bash deploy/install_prod.sh` |
| `Refusing to overwrite existing file` | Installer защищает существующий env; не удаляйте его на действующем сервере |
| `POSTGRES_PASSWORD is required` | Env отсутствует или неполон; на новой VM используйте генератор, на действующем сервере выполните контролируемое восстановление настроек |
| `SECRET_KEY is standard...` | Production отклоняет стандартный или слабый ключ; требуется безопасная ротация |
| Ошибка регистрации администратора | Установка не завершена; проверьте ввод и логи, не передавая пароль в командной строке |
| Ошибка миграций | Диагностируйте `alembic upgrade head`; не заменяйте миграции `create_all` |
| Нет доступа в `/opt/fitintel-pro` после установки | Это ожидаемая защита; используйте `sudo -s` |
| Нет сети при установке с флешки | Код можно перенести, но текущие build/pull требуют интернет; полностью offline-режим не поддерживается |

## 16. Контрольный чек-лист

- [ ] Установлен ожидаемый commit `main`.
- [ ] `deploy/.env` создан именно на этом сервере и имеет права `0600`.
- [ ] В env нет стандартных или скопированных с прежнего клуба секретов.
- [ ] Миграции Alembic завершились успешно.
- [ ] Первый администратор создан через скрытую регистрацию с подтверждением пароля.
- [ ] `db`, `redis`, `api`, `nginx` и `celery-worker` работают.
- [ ] Health API отвечает успешно.
- [ ] HTTPS и доверенный сертификат проверены.
- [ ] Лицензия активирована, вход администратора выполнен.
- [ ] Каталог установки доступен только через полномочия ОС администратора.
- [ ] Настроен и проверен резервный архив.
- [ ] Restore-test выполнен на отдельном стенде.

---

Руководство обновлено: **2026-10-26**.
