# FitIntel Pro — Установка и настройка сервера (Linux)

Проверено на: **Ubuntu 24.04** (также подходит Debian 11+). Сборка из исходников через Docker.

---

## 1. Требования

- Ubuntu 20.04+ / Debian 11+ (чистая машина или VM)
- Минимум: 2 CPU, 4 GB RAM, 20 GB диск
- Открытые порты: **80** (nginx), **22** (SSH)
- Доступ в интернет

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

## 5. Первый запуск (сборка 10–30 мин — компилируется dlib!)

```bash
cd ~/fitintel-pro/deploy
docker compose -f docker-compose.test.yml up -d --build
docker compose -f docker-compose.test.yml ps
```

Все 5 контейнеров должны быть `running`: db (healthy), redis, api (healthy), nginx, celery-worker.

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

- Используйте **латиницу** в логине и пароле.
- Пароль — минимум 8 символов.
- Email — с реальным доменом (НЕ .local/.test/.invalid — валидатор их отвергает).
- Повторный запуск с другими `-e` НЕ меняет данные существующего админа (сидер пропускает существующего). Чтобы сменить креды уже созданному админу — через desktop («Пользователи») или SQL:
  ```bash
  docker compose -f docker-compose.test.yml exec db psql -U fitnexus_user -d fitnexus_ai -c "UPDATE users SET email='новая@почта.ru' WHERE username='admin';"
  ```

## 8. Проверка сервера

```bash
curl -s http://localhost/api/v1/health/
# {"status":"ok","app":"FitIntel Pro","module":"crm","database":"ok"}
```

## 9. Подключение desktop (Windows)

1. Узнать IP сервера: `ip a | grep "inet " | grep -v 127.0.0.1`
2. С Windows-ПК: `curl.exe -s http://<IP>/api/v1/health/` — должен вернуть тот же JSON
3. В `fitintel-desktop\client_settings.json` указать:
   ```json
   "api_base": "http://<IP>/api/v1"
   ```
4. Запустить desktop (через `restart_desktop.ps1`) → вход с созданным логином/паролем
5. **Сразу сменить пароль**, если оставляли дефолтный

## 10. Обновление сервера

```bash
cd ~/fitintel-pro && git pull
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
docker compose -f docker-compose.test.yml exec db psql -U fitnexus_user -d fitnexus_ai -c "SELECT username, email FROM users;"
# Бэкап БД
docker compose -f docker-compose.test.yml exec db pg_dump -U fitnexus_user fitnexus_ai | gzip > backup_$(date +%F).sql.gz
# ПОЛНЫЙ сброс (ВСЕ ДАННЫЕ УДАЛЯТСЯ!): затем шаги 5–7 заново
docker compose -f docker-compose.test.yml down -v
```

---

## Решение типовых проблем

| Симптом | Решение |
|---|---|
| `No matching distribution found for pywin32` | Уже исправлено в репо (маркер `sys_platform == "win32"`) |
| Сборка падает на dlib/face-recognition | Уже исправлено (gcc/g++/cmake в Dockerfile) |
| `alembic` лезет на 127.0.0.1 | Уже исправлено (URL из переменных окружения) |
| `ModuleNotFoundError: No module named 'app'` | Запускать `python -m scripts.x`, не `python scripts/x.py` |
| `relation "..." does not exist` | Выполнить `python -m scripts.bootstrap_db` |
| `500` на /auth/me, «special-use or reserved name» в email | Email с реальным доменом (не .local/.test) |
| `celery-worker (unhealthy)` | Уже исправлено (`healthcheck: disable`) |
| `DatatypeMismatch: integer and uuid` | Уже исправлено (модели приведены к UUID) |
| Desktop не может войти | Проверить `api_base` в client_settings.json и что порт 80 открыт |

## Безопасность (перед боевым продом!)

1. Сменить ВСЕ пароли по умолчанию (БД, admin)
2. Свой `SECRET_KEY` в `.env`
3. Firewall: `sudo ufw allow 80,443/tcp && sudo ufw enable`
4. SSL: `docker-compose.prod.yml` + сертификаты в `deploy/nginx/ssl/`
5. Регулярные бэкапы БД (команда выше) + выгрузка на другой носитель

---
*FitIntel Pro v1.5.x | Инструкция: 2026-09-24*

## 12. Мониторинг и логи

    cd ~/fitintel-pro/deploy/monitoring
    docker compose -f docker-compose.monitoring.yml up -d

Grafana: http://<IP>:3000 (admin/admin) — дашборды подгружаются автоматически.
Логи всех контейнеров: Grafana -> Explore -> Loki -> {container="deploy-api-1"}.

## 13. Автобэкап БД (03:00 ежедневно)

    bash ~/fitintel-pro/scripts/backup/install_cron.sh

Одна команда создаёт конфиг и ставит cron. Хранилища в backup.env:
LOCAL_DIR / HDD_ENABLE+HDD_MOUNT / CLOUD_ENABLE+rclone.
Лог: /var/log/fitintel-backup.log
