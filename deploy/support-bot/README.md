# Support Bot — развёртывание на 125 (debianNOUT)

Изолированный контур. НЕ изменяет: platform (compose/db), mailcow, rustdesk,
wireguard-hub, php-фронт fixintel.ru. Откат — `docker compose down -v` + убрать location.

## Как бот идентифицирует клуб (по ТЗ, без изменений платформы)
1. Пользователь присылает ключ лицензии (FIPRO-...)
2. GET http://platform-wireguard-1:8002/platform/clubs (заголовок X-Client-CN)
   -> матчит клуб по первым 12 символам ключа
3. GET /platform/clubs/{slug}/license -> статус active|grace -> привязка
⚠ platform_api живёт в netns контейнера wireguard (network_mode: service:wireguard),
  обращение идёт на platform-wireguard-1:8002, а НЕ platform-platform_api-1.

## Контракт MAX (сверен с dev.max.ru, 06.11.2026)
- Подписка: POST /subscriptions {url, update_types:["message_created","bot_started"], secret}
  секрет: [a-zA-Z0-9_-]{5,256} (openssl rand -hex подходит)
- Webhook: объект Update; секрет в заголовке X-Max-Bot-Api-Secret; ответ 200 ≤ 30 с
- Отправка: POST /messages?user_id=... Authorization: <token>
- Вложения: POST /uploads?type=image -> {url, token} -> multipart на url ->
  attachments=[{type:"image", payload:{token}}]
- База API: по умолчанию platform-api.max.ru (prod). MAX в доках советует platform-api2 —
  если потребуется, переключите MAX_API_BASE в .env.

## Структура в репозитории
    support_bot/               Dockerfile, app.py, kb_import.py, requirements.txt
    deploy/support-bot/        docker-compose.yml, migrations/001_init.sql, README.md, .env

## 1–2. Файлы уже в репо; 125 синхронизирован
## 3. .env (5 переменных; токен MAX пока placeholder)
    cd /home/andrei/fitintel-pro/deploy/support-bot
    wc -l .env   # маркер: 5 .env

## 4. БД
    docker compose up -d support-bot-db
    docker exec support-bot-db psql -U support_bot -d support_bot -c '\dt'   # маркер: 6 таблиц

## 5. Импорт KB (идемпотентно; повторять после обновления docs/kb/)
    docker compose run --rm support-bot python kb_import.py /kb_source   # маркер: IMPORTED=~120
    docker exec support-bot-db psql -U support_bot -d support_bot -tAc 'SELECT count(*) FROM kb_articles'  # та же цифра

## 6. Сборка и запуск бота
    docker compose up -d --build support-bot
    curl -s http://192.168.101.125:8091/health   # ожидание: {"status":"ok","kb_articles":NNN}
    docker logs support-bot --tail 20            # без traceback

## 7. fixintel-nginx: добавочный location (единственное изменение чужого конфига)
    location /bot/ {
        proxy_pass http://192.168.101.125:8091/bot/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Max-Bot-Api-Secret $http_x_max_bot_api_secret;
        client_max_body_size 10m;
    }
    # docker exec fixintel-nginx nginx -t && docker exec fixintel-nginx nginx -s reload

## 8. Подписка webhook (после выдачи боевого токена MAX; подставить токен и секрет из .env)
    curl -X POST "https://platform-api.max.ru/subscriptions"       -H "Authorization: <MAX_SUPPORT_BOT_TOKEN>" -H "Content-Type: application/json"       -d '{"url":"https://fixintel.ru/bot/webhook","update_types":["message_created","bot_started"],"secret":"<BOT_WEBHOOK_SECRET>"}'

## 9. Первый админ поддержки (ваш MAX user_id)
    docker exec support-bot-db psql -U support_bot -d support_bot       -c "INSERT INTO bot_admins (max_user_id, name, role) VALUES ('<MAX_USER_ID>','Андрей','superadmin') ON CONFLICT DO NOTHING;"

## Откат
    cd /home/andrei/fitintel-pro/deploy/support-bot && docker compose down -v
    docker network disconnect platform_default support-bot 2>/dev/null; true
    # убрать location /bot/ из nginx и reload

## Открытые точки (фаза 3)
    - маршрутизация админских ответов по reply/quote (посмотреть реальный Update)
    - дежурства support_schedule -> выбор дежурного при эскалации
