# Support Bot — развёртывание на 125 (debianNOUT)

Изолированный контур. НЕ изменяет: platform (compose/db), mailcow, rustdesk,
wireguard-hub, php-фронт fixintel.ru. Откат — `docker compose down -v` + убрать location.

## Как бот идентифицирует клуб (по ТЗ, без изменений платформы)
1. Пользователь присылает ключ лицензии (FIPRO-...)
2. Бот: GET http://platform-wireguard-1:8002/platform/clubs (заголовок X-Client-CN)
   -> матчит клуб по первым 12 символам ключа
3. Бот: GET /platform/clubs/{slug}/license -> статус active|grace -> привязка
   (blocked/no_license -> «обратитесь к администратору платформы»)
⚠ platform_api живёт в netns контейнера wireguard (network_mode: service:wireguard),
  поэтому обращение идёт на platform-wireguard-1:8002, а НЕ platform-platform_api-1.

## Структура в репозитории
    support_bot/               Dockerfile, app.py, kb_import.py, requirements.txt
    deploy/support-bot/        docker-compose.yml, migrations/001_init.sql, README.md, .env

## 1. ПК: файлы уже в репо (коммит support-bot skeleton + правки контракта)
## 2. 125: синхронизация репо
    cd /home/andrei/fitintel-pro && git fetch origin && git reset --hard origin/main

## 3. 125: .env (пароли генерируем; токен MAX — после создания бота в кабинете MAX)
    cd /home/andrei/fitintel-pro/deploy/support-bot
    printf 'SUPPORT_BOT_DB_PASSWORD=%s
BOT_WEBHOOK_SECRET=%s
MAX_SUPPORT_BOT_TOKEN=
PLATFORM_ADMIN_CN=andrei@fitintel.local
ALLOWED_LICENSE_STATUSES=active,grace
'       "$(openssl rand -hex 16)" "$(openssl rand -hex 16)" > .env
    wc -l .env   # маркер: 5 строк; значения не светим

## 4. 125: БД + схема (свой контейнер, platform_db не трогаем)
    docker compose up -d support-bot-db
    docker exec support-bot-db psql -U support_bot -d support_bot -c '\dt'   # маркер: 6 таблиц

## 5. 125: импорт KB (идемпотентно; повторять после каждого обновления docs/kb/)
    docker compose run --rm support-bot python kb_import.py /kb_source   # маркер: IMPORTED=~120
    docker exec support-bot-db psql -U support_bot -d support_bot -tAc 'SELECT count(*) FROM kb_articles'

## 6. 125: сборка и запуск бота + маркеры
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
    - формат payload webhook MAX (reply/quote) -> точная маршрутизация админских ответов
    - MAX_UPLOAD_PATH: механика вложений scr-*.png
    - support_schedule -> выбор дежурного админа при эскалации
