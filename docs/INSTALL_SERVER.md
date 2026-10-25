# FitIntel Pro — Установка и настройка сервера (полное руководство)

Проверено на: **Ubuntu 24.04** (также подходит Debian 11+). Сборка из исходников через Docker.
Актуально для: **FitIntel Pro v1.5.x**

---

## Содержание

1. [Требования](#1-Требования)
2. [Установка Docker](#2-Установка-Docker)
3. [Получение кода](#3-Получение-кода-приватный-репозиторий)
4. [Конфигурация (опционально)](#4-Конфигурация-опционально)
5. [Первый запуск (сборка)](#5-Первый-запуск-сборка-10–30-мин)
6. [Инициализация базы данных](#6-Инициализация-базы-данных)
7. [Создание администратора](#7-Создание-администратора-свои-логин--пароль--email)
8. [Проверка сервера](#8-Проверка-сервера)
9. [Подключение desktop (Windows)](#9-Подключение-desktop-windows)
10. [Обновление сервера](#10-Обновление-сервера)
11. [Полезные команды](#11-Полезные-команды)
12. [Мониторинг, логи и дашборды](#12-Мониторинг-логи-и-дашборды-всё-автоматически)
13. [Автобэкап клуба](#13-Автобэкап-клуба-systemd-timer)
14. [Чек-лист после установки](#14-Чек-лист-после-установки-2-минуты)

---

## 1. Требования

- Ubuntu 20.04+ / Debian 11+ (чистая машина или VM)
- Минимум: 2 CPU, 4 GB RAM, 20 GB диск
- Открытые порты: **80** (nginx/API), **22** (SSH)
- Для мониторинга дополнительно: **3000** (Grafana), **9090** (Prometheus) — только для админов
- Доступ в интернет (загрузка образов и пакетов)

## 2. Установка Docker

```bash
sudo apt update && sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
docker --version && docker compose version
```

> Для Debian замените в двух местах `linux/ubuntu` на `linux/debian`.
> Если `newgrp` не переключил группу — выйдите и зайдите по SSH заново.

## 3. Получение кода (приватный репозиторий)

GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic) → галочка **repo** → скопируйте токен (показывается один раз!).

```bash
cd ~
git clone https://<ТОКЕН>@github.com/Kant84/fitintel-pro.git
cd fitintel-pro
git checkout main
```

После клонирования токен можно удалить на GitHub.

## 4. Конфигурация (опционально)

Тестовый профиль работает «из коробки». Для своих значений создайте файл `deploy/.env`:

```env
POSTGRES_DB=fitnexus_ai
POSTGRES_USER=fitnexus_user
POSTGRES_PASSWORD=СложныйПарольБД
SECRET_KEY=ДлиннаяСлучайнаяСтрокаМинимум32Символа
```

## 5. Первый запуск (сборка 10–30 мин)

```bash
cd ~/fitintel-pro/deploy
docker compose -f docker-compose.test.yml up -d --build
docker compose -f docker-compose.test.yml ps
# Автоматически установить полный ежедневный бэкап и запуск после перезагрузки VM
bash backup/install_cron.sh
```

Все 5 контейнеров должны быть `running`: db (healthy), redis, api (healthy), nginx, celery-worker.
При первой сборке компилируется dlib — это долго, **не прерывайте**.

## 6. Инициализация базы данных

```bash
cd ~/fitintel-pro/deploy
# Таблицы по моделям + фиксация миграций
docker compose -f docker-compose.test.yml exec api python -m scripts.bootstrap_db
# Справочники: роли, права
docker compose -f docker-compose.test.yml exec api python -m app.db.seed.run_seed
```

> **Важно:** запускать через `python -m` (а не `python scripts/...`) — иначе модуль `app` не найдется.

## 7. Создание администратора (СВОИ логин / пароль / email)

По умолчанию: `admin` / `Admin123!ChangeMe` / `admin@fitnexus.ru`.
**Задать свои данные при создании:**

```bash
cd ~/fitintel-pro/deploy
docker compose -f docker-compose.test.yml exec \
  -e SEED_ADMIN_EMAIL="ваша@почта.ru" \
  -e SEED_ADMIN_USERNAME="ВашЛогин" \
  -e SEED_ADMIN_PASSWORD="ВашПарольМинимум8Символов" \
  api python -m app.db.seed.seed_admin
```

- Логин и пароль — **латиницей**, пароль минимум 8 символов.
- Email — с реальным доменом (НЕ .local/.test/.invalid — валидатор их отвергает).
- Повторный запуск с другими `-e` НЕ меняет данные существующего админа. Смена кредов существующему — через desktop («Пользователи») или SQL:
  ```bash
  docker compose -f docker-compose.test.yml exec db psql -U fitnexus_user -d fitnexus_ai \
    -c "UPDATE users SET email='новая@почта.ru' WHERE username='admin';"
  ```

## 8. Проверка сервера

```bash
curl -s http://localhost/api/v1/health/
# {"status":"ok","app":"FitIntel Pro","module":"crm","database":"ok"}
```

## 9. Подключение desktop (Windows)

1. Узнать IP сервера: `ip a | grep "inet " | grep -v 127.0.0.1`
2. С Windows-ПК: `curl.exe -s http://<IP>/api/v1/health/` — должен вернуть тот же JSON
3. В файле `fitintel-desktop\client_settings.json` указать:
   ```json
   "api_base": "http://<IP>/api/v1"
   ```
4. Запустить desktop (через `restart_desktop.ps1`) → вход с созданным логином/паролем
5. **Сразу сменить пароль**, если оставляли дефолтный

## 10. Обновление сервера

```bash
cd ~/fitintel-pro && git pull
# Обновить права backup.sh и расписание без ручной настройки cron
bash deploy/backup/install_cron.sh
cd deploy
docker compose -f docker-compose.test.yml up -d --build
# при изменении моделей:
docker compose -f docker-compose.test.yml exec api alembic upgrade head
```

## 11. Полезные команды

```bash
# Логи API без health-спама
docker compose -f docker-compose.test.yml logs -f api 2>&1 | grep -v health
# Статус контейнеров
docker compose -f docker-compose.test.yml ps
# Перезапуск сервиса
docker compose -f docker-compose.test.yml restart api
# Консоль внутри контейнера
docker compose -f docker-compose.test.yml exec api bash
# SQL напрямую
docker compose -f docker-compose.test.yml exec db psql -U fitnexus_user -d fitnexus_ai \
  -c "SELECT username, email FROM users;"
# ПОЛНЫЙ сброс (ВСЕ ДАННЫЕ УДАЛЯТСЯ!): затем шаги 5–7 заново
docker compose -f docker-compose.test.yml down -v
```

---

## 12. Мониторинг, логи и дашборды (всё автоматически)

```bash
cd ~/fitintel-pro/deploy/monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

Поднимается 7 контейнеров: Prometheus, Grafana, Loki, Promtail, node-exporter,
cAdvisor, Alertmanager. **Дашборды и источники данных подгружаются автоматически**
(провиженинг из репозитория) — ничего настраивать вручную не нужно.

| Сервис | Адрес | Назначение |
|---|---|---|
| Grafana | http://<IP>:3000 (admin/admin) | дашборды и просмотр логов |
| Prometheus | http://<IP>:9090/targets | метрики, состояние таргетов |
| Loki | http://<IP>:3100 | хранилище логов (Promtail шлёт автоматически) |

**Дашборды** (Grafana → Dashboards → папка «FitIntel Pro»):
- **«FitIntel API»** — запросов/сек, ошибки 5xx %, p95 латентность, запросы по статусам,
  топ-5 медленных путей, панель логов Loki
- **«FitIntel System»** — CPU/RAM/диск сервера, таргеты up, топ-5 контейнеров по CPU/RAM

**Логи:** Grafana → Explore → источник «Loki» → запрос `{container="deploy-api-1"}`.
Promtail собирает логи **всех** контейнеров автоматически. Посмотреть список:
```bash
curl -s http://localhost:3100/loki/api/v1/label/container/values
```

**Алерты:** правила в `prometheus/rules/fitintel.yml` (HighErrorRate, APIDown, DiskSpaceLow и др.).
Alertmanager слушает на :9093. Для отправки уведомлений отредактируйте
`alertmanager/alertmanager.yml` (добавьте receiver: email/Telegram/webhook).

## 13. Автобэкап клуба (systemd timer)

**Обязательный шаг на новом сервере и при обновлении backup-установщика:**

    bash ~/fitintel-pro/deploy/backup/install_cron.sh

Этот вызов уже включён в шаги 5 и 10. Пока установка backup не встроена в общий автоустановщик, это единственный отдельный шаг его настройки. Сам Dockerfile unit-файлы на хост не устанавливает и меняться не должен.

После одного вызова больше не требуются ручные `chmod`, настройка cron или редактирование `/etc/systemd/system`:

- На Ubuntu с systemd устанавливаются `fitintel-backup.service` и `fitintel-backup.timer`.
- Timer включён в автозагрузку: ежедневно в **21:30** и через **60 секунд после загрузки VM**.
- `Persistent=true` выполняет пропущенное задание после включения сервера.
- Service работает от root и сохраняет защищённые секреты; при необходимости установщик запросит `sudo`.
- Если systemd недоступен, автоматически используется cron fallback.
- Прежние строки FitIntel backup удаляются из пользовательского и root cron. Другие задания, включая media-backup, сохраняются.
- Пересборка Dockerfile и образов не нужна: timer работает на хосте Ubuntu.

Архив `fitintel_full_ДАТА.tar.gz` создаётся в `~/fitintel-pro/deploy/backups/` и включает PostgreSQL, accounting SQLite, медиа и файлы Docker-томов, лицензию, `deploy/.env`, `/etc/fitintel/secrets`, SSL/platform-сертификаты и доступные локальные настройки.

Архив имеет права `0600`; секреты не выводятся в журнал. Храните копию вне сервера. Ротация — **14 дней**. Полные копии медиа требуют достаточного свободного места.

Проверка timer и ручной запуск:

    systemctl list-timers fitintel-backup.timer --no-pager
    sudo systemctl start fitintel-backup.service
    sudo systemctl status fitintel-backup.service --no-pager
    sudo journalctl -u fitintel-backup.service -n 20 --no-pager

Проверка архива:

    latest=$(sudo ls -1t ~/fitintel-pro/deploy/backups/fitintel_full_*.tar.gz | head -1)
    sudo stat -c '%a %s %n' "$latest"
    sudo tar -tzf "$latest" | head -30

Внутри должны быть `database.sql.gz`, `accounting.sqlite`, `files.tar.gz`, `MANIFEST.txt` и `settings/`. Полное восстановление выполняйте на остановленных сервисах отдельного стенда, не распаковывая архив поверх работающего клуба.


## 14. Чек-лист после установки (2 минуты)

- [ ] Сменить пароль admin (desktop → «Пользователи»)
- [ ] Сменить пароль Grafana (administration → Users → admin; дефолт admin/admin)
- [ ] Firewall: `sudo ufw allow 80,3000,9090/tcp && sudo ufw enable`
- [ ] Проверить свежий дамп в `deploy/backups/` и строки `deploy/backup/backup.sh` в `crontab -l`
- [ ] Открыть дашборды Grafana и проверить логи Loki

---

## Решение типовых проблем

| Симптом | Решение |
|---|---|
| `No matching distribution found for pywin32` | Уже исправлено в репо (маркер `sys_platform == "win32"`) |
| Сборка падает на dlib/face-recognition | Уже исправлено (gcc/g++/cmake в Dockerfile) |
| `alembic` лезет на 127.0.0.1 | Уже исправлено (URL БД из переменных окружения) |
| `ModuleNotFoundError: No module named 'app'` | Запускать `python -m scripts.x`, не `python scripts/x.py` |
| `relation "..." does not exist` | Выполнить `python -m scripts.bootstrap_db` |
| `500` на /auth/me, «special-use or reserved name» | Email с реальным доменом (не .local/.test) |
| `DatatypeMismatch: integer and uuid` | Уже исправлено (модели приведены к UUID) |
| Desktop не может войти | Проверить `api_base` в client_settings.json и доступность порта 80 |
| Loki перезапускается | Уже исправлено в репо (`user: "0"` в compose) |
| Порядок URL: 307 Redirect | Использовать слэш в конце пути (`/clients/`, `/tariffs/`) или `python -m` |

## Безопасность (перед боевым продом!)

1. Сменить ВСЕ пароли по умолчанию (БД, admin, Grafana)
2. Свой `SECRET_KEY` в `deploy/.env`
3. Firewall: только 80/443 наружу, Grafana/Prometheus — внутри сети или за VPN
4. SSL: `docker-compose.prod.yml` + сертификаты в `deploy/nginx/ssl/`
5. Регулярные бэкапы БД (раздел 13) + выгрузка на другой носитель
6. Токен GitHub после клонирования — удалить; обновления — через новый токен

---
*FitIntel Pro v1.5.x | Руководство обновлено: 2026-09-25*
