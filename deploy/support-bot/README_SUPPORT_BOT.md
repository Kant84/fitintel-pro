# Support Bot — развёртывание на 125 (debianNOUT)

Изолированный контур. НЕ изменяет: platform (compose/db), mailcow, rustdesk,
wireguard-hub, php-фронт fixintel.ru. Откат — `docker compose down -v` + убрать location.

## Структура в репозитории
    support_bot/               Dockerfile, app.py, kb_import.py, requirements.txt
    deploy/support-bot/        docker-compose.yml, migrations/001_init.sql, .env

## 1. ПК: коммит и push файлов в репо (ветка main)
## 2. 125: синхронизация репо
    cd /home/andrei/fitintel-pro && git fetch origin && git reset --hard origin/main

## 3. 125: .env (пароли генерируем, токен MAX — после создания бота в кабинете MAX)
    cd /home/andrei/fitintel-pro/deploy/support-bot
    printf 'SUPPORT_BOT_DB_PASSWORD=%s
BOT_WEBHOOK_SECRET=%s
MAX_SUPPORT_BOT_TOKEN=
CLUB_CHECK_PATH=/api/v1/clubs/check_license
'       "$(openssl rand -hex 16)" "$(openssl rand -hex 16)" > .env
    cat .env | sed -E 's/=.*/=<задано>/'   # маркер: 4 строки, значения не светим

## 4. 125: БД + схема
    docker compose up -d support-bot-db
    docker exec support-bot-db psql -U support_bot -d support_bot -c '\dt'   # маркер: 6 таблиц

## 5. 125: импорт KB (идемпотентно, повторяется после каждого обновления docs/kb/)
    docker compose run --rm support-bot python kb_import.py /kb_source   # маркер: IMPORTED=~120
    docker exec support-bot-db psql -U support_bot -d support_bot -tAc 'SELECT count(*) FROM kb_articles'

## 6. 125: запуск бота + маркеры
    docker compose up -d
    curl -s http://192.168.101.125:8091/health        # ожидание: {"status":"ok","kb_articles":N}
    docker logs support-bot --tail 20                 # без traceback

## 7. fixintel-nginx: добавочный location (единственное изменение чужого конфига)
    location /bot/ {
        proxy_pass http://192.168.101.125:8091/bot/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Webhook-Secret $http_x_webhook_secret;
        client_max_body_size 10m;
    }
    # проверка и применение: docker exec fixintel-nginx nginx -t && docker exec fixintel-nginx nginx -s reload

## 8. Кабинет MAX: webhook бота = https://fixintel.ru/bot/webhook, секрет = BOT_WEBHOOK_SECRET
## 9. SQL: первый админ поддержки (ваш MAX user_id)
    docker exec support-bot-db psql -U support_bot -d support_bot       -c "INSERT INTO bot_admins (max_user_id, name, role) VALUES ('<MAX_USER_ID>','Андрей','superadmin') ON CONFLICT DO NOTHING;"

## Откат
    cd /home/andrei/fitintel-pro/deploy/support-bot && docker compose down -v
    docker network disconnect platform_default support-bot 2>/dev/null; true
    # убрать location /bot/ из nginx и reload

## Открытые точки (фаза 2, после выдачи боевого токена MAX)
    - CLUB_CHECK_PATH: сверить с реальным роутом platform_api (read-only grep по исходникам)
    - формат payload webhook MAX (reply/quote) -> точная маршрутизация админских ответов
    - MAX_UPLOAD_PATH: механика вложений scr-*.png
    - support_schedule -> выбор дежурного админа при эскалации
