# Web Push — настройка уведомлений (FitIntel Pro)

Уведомления из FitIntel в браузер (сотрудник — ПК, клиент — телефон).
Доходят до устройства даже при свёрнутом браузере/закрытом приложении.

Цепочка: сервер клуба (VAPID-ключи) → страница подписки → браузер подписывается →
сервер отправляет → push-сервис (Google/Apple) → тост/баннер на устройстве.
У каждого клуба СВОЯ пара ключей и СВОИ подписчики.

---

## ЧАСТЬ 1. НАСТРОЙКА КЛУБА (один раз)

### 1.1. Включить Web Push и задать VAPID sub

**Объяснение.** VAPID sub — «обратный адрес» в каждом пуше. Apple строго
проверяет его: если домен нереальный (`.local`, выдуманный) — все пуши на
iPhone отклоняются ошибкой `403 BadJwtToken`. Без sub из настроек отправка
отказывает с понятной ошибкой.

**Действие.** Desktop → «Уведомления → Web Push»:
- включить «Web Push»;
- поле **«VAPID sub»** заполнить: `mailto:адрес@реальный-домен.клуба`
  (или `https://домен.клуба`). Если пусто — подставится «Email поддержки»
  из «Коммерция → White-label».

**Результат.** Настройки сохранены, отправка не будет отклонена Apple.

### 1.2. Сгенерировать пару VAPID-ключей

**Объяснение.** Ключи подписывают пуши. Генерируются один раз; при смене ключей
все подписчики должны переподписаться.

**Команда** (на сервере клуба):

```bash
sudo -i
cd &lt;каталог-проекта-клуба&gt;        # пример: /opt/fitintel-pro
COMPOSE=(docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml)

"${COMPOSE[@]}" exec -T api python - &lt;&lt;'PY'
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from sqlalchemy import text
from app.db.session import engine
import base64

sk = ec.generate_private_key(ec.SECP256R1())
der = sk.private_bytes(serialization.Encoding.DER,
    serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
priv = base64.urlsafe_b64encode(der).rstrip(b'=').decode()
pub = base64.urlsafe_b64encode(
    sk.public_key().public_bytes(serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint)).rstrip(b'=').decode()

from py_vapid import Vapid
Vapid.from_string(private_key=priv)          # проверка формата

with engine.begin() as c:
    c.execute(text("UPDATE notification_settings SET webpush_enabled=true, "
                   "vapid_private=:p, vapid_public=:u WHERE id=1"),
              {"p": priv, "u": pub})
print('KEYS_OK=1')
PY
```

**Результат.** В консоли `KEYS_OK=1`; проверка (ожидается `t|t`):

```bash
"${COMPOSE[@]}" exec -T db psql -U "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_USER"')" \
  -d "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_DB"')" -Atc \
"SELECT webpush_enabled, vapid_public IS NOT NULL FROM notification_settings WHERE id=1;"
```

---

## ЧАСТЬ 2. ПУБЛИКАЦИЯ КЛУБА (HTTPS-доступ, один раз)

**Объяснение.** Страница подписки работает только по HTTPS с доверенным
сертификатом (иначе браузер не даст подписаться). Два варианта:
**А.** Поддомен через платформу (клуб без белого адреса) — описан ниже.
**Б.** Собственный белый адрес клуба — платформа не нужна, клуб сам берёт
сертификат (certbot в любом образе).

### 2.1. DNS

**Действие.** В панели регистратора домена платформы: «Добавить запись» →
тип `A` → имя `&lt;клуб&gt;` → значение = **белый IP платформы** (тот, на который
смотрит A-запись домена платформы).

**Команда-проверка:**

```bash
dig +short A &lt;клуб&gt;.&lt;домен-платформы&gt; @&lt;DNS-сервер-провайдера&gt;
```

**Результат.** Возвращается белый IP платформы.

### 2.2. Прокси на фронте платформы (контейнер nginx)

**Объяснение.** На платформе 80/443 уже заняты фронт-контейнером nginx —
системный nginx не используем, остальные контейнеры (почта, платформа, VPN)
не трогаем. Конфиги фронта лежат на хосте в каталоге conf.d фронт-контейнера.

**Действие.** Создать файл `&lt;клуб&gt;.conf` в conf.d фронта с HTTP-server:

```nginx
server {
    listen 80;
    server_name &lt;клуб&gt;.&lt;домен-платформы&gt;;
    location /.well-known/acme-challenge/ { root /var/www/certbot; allow all; }
    location / { proxy_pass http://&lt;LAN-IP-клуба&gt;:80;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; }
}
```

**Команда:**

```bash
docker exec &lt;фронт-nginx&gt; nginx -t && docker exec &lt;фронт-nginx&gt; nginx -s reload
```

**Результат.** `syntax is ok` + `test is successful`; HTTP-прокси отвечает.

### 2.3. Сертификат Let's Encrypt (webroot через тот же фронт)

**Команды:**

```bash
certbot certonly --webroot -w &lt;путь-к-webroot-certbot-на-хосте&gt; \
  -d &lt;клуб&gt;.&lt;домен-платформы&gt; --non-interactive --agree-tos -m &lt;email&gt;

mkdir -p &lt;путь-к-ssl-на-хосте&gt;/&lt;клуб&gt;
cp /etc/letsencrypt/live/&lt;клуб&gt;.&lt;домен-платформы&gt;/fullchain.pem &lt;путь-к-ssl-на-хосте&gt;/&lt;клуб&gt;/
cp /etc/letsencrypt/live/&lt;клуб&gt;.&lt;домен-платформы&gt;/privkey.pem  &lt;путь-к-ssl-на-хосте&gt;/&lt;клуб&gt;/
```

**Результат.** Сертификат выпущен и лежит там, где его видит фронт-контейнер.

### 2.4. HTTPS-server в том же `&lt;клуб&gt;.conf`

**Действие.** Дописать в файл два server-блока (80-й редиректит, 443 работает):

```nginx
server {
    listen 80;
    server_name &lt;клуб&gt;.&lt;домен-платформы&gt;;
    location /.well-known/acme-challenge/ { root /var/www/certbot; allow all; }
    location / { return 301 https://$server_name$request_uri; }
}
server {
    listen 443 ssl;
    server_name &lt;клуб&gt;.&lt;домен-платформы&gt;;
    ssl_certificate     /etc/nginx/ssl/&lt;клуб&gt;/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/&lt;клуб&gt;/privkey.pem;
    location / {
        proxy_pass http://&lt;LAN-IP-клуба&gt;:80;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
        client_max_body_size 20m;
    }
}
```

**Команда:** `docker exec &lt;фронт-nginx&gt; nginx -t && docker exec &lt;фронт-nginx&gt; nginx -s reload`

### 2.5. Авто-продление сертификата

**Объяснение.** Сертификат живёт 90 дней; certbot продлевает сам, а
deploy-hook копирует новые файлы и перезагружает фронт.

**Действие.** Файл `/etc/letsencrypt/renewal-hooks/deploy/&lt;клуб&gt;.sh`:

```bash
#!/bin/sh
cp /etc/letsencrypt/live/&lt;клуб&gt;.&lt;домен-платформы&gt;/fullchain.pem &lt;путь-к-ssl-на-хосте&gt;/&lt;клуб&gt;/fullchain.pem
cp /etc/letsencrypt/live/&lt;клуб&gt;.&lt;домен-платформы&gt;/privkey.pem  &lt;путь-к-ssl-на-хосте&gt;/&lt;клуб&gt;/privkey.pem
docker exec &lt;фронт-nginx&gt; nginx -s reload
```

**Команда:** `chmod +x /etc/letsencrypt/renewal-hooks/deploy/&lt;клуб&gt;.sh`

### 2.6. Проверка публикации

**Команды:**

```bash
curl -sS https://&lt;клуб&gt;.&lt;домен-платформы&gt;/api/v1/health/    # ожидается JSON {"status":"ok",...}
echo | openssl s_client -connect &lt;LAN-IP-фронта&gt;:443 -servername &lt;клуб&gt;.&lt;домен-платформы&gt; 2&gt;/dev/null | openssl x509 -noout -subject
```

**Результат.** Health вернул JSON, subject сертификата = `&lt;клуб&gt;.&lt;домен-платформы&gt;`.

---

## ЧАСТЬ 3. ПОДПИСКА УСТРОЙСТВ

### 3.1. ПК (Windows/macOS/Linux) — персонал

**Действие.**
1. Chrome/Edge: `https://&lt;адрес-клуба&gt;/api/v1/notify/webpush/page`
2. «Подписаться» → разрешить уведомления → «Подписка сохранена».

**Результат.** Тост Windows после тестовой отправки (см. 4.1).

*Проверка в локальной сети без HTTPS:* CMD от администратора:
`netsh interface portproxy add v4tov4 listenport=8080 listenaddress=127.0.0.1 connectport=80 connectaddress=&lt;LAN-IP-сервера&gt;`,
открывать `http://localhost:8080/api/v1/notify/webpush/page` (localhost — безопасный контекст).
Убрать: `netsh interface portproxy delete v4tov4 listenport=8080 listenaddress=127.0.0.1`.

### 3.2. Android — клиент/персонал

**Действие.**
1. Chrome на телефоне: `https://&lt;адрес-клуба&gt;/api/v1/notify/webpush/page`
2. «Подписаться» → разрешить.

**Результат.** Пуши приходят из любой сети (доставку делает Google). Никаких
дополнительных действий пользователя не требуется.

### 3.3. iOS (iPhone/iPad) — только через PWA, имя = клуб

**Объяснение.** Apple разрешает веб-пуш только из веб-приложения, установленного
на «Экран Домой» (iOS 16.4+). Имя и иконка приложения — название клуба из
«Коммерция → White-label» (подтягивается из PWA-манифеста автоматически).

**Действие.**
1. **Safari** (не Chrome, не MAX): открыть `https://&lt;адрес-клуба&gt;/api/v1/notify/webpush/page`.
2. «Поделиться» → «На экран Домой» → «Добавить». На рабочем столе — иконка с именем клуба.
3. Запустить **с иконки** → «Подписаться» → разрешить уведомления → «Подписка сохранена».

**Результат.** Баннер на iPhone приходит даже когда приложение свёрнуто.

---

## ЧАСТЬ 4. ЭКСПЛУАТАЦИЯ

### 4.1. Тестовая отправка всем подписчикам

**Команда:**

```bash
curl -sS -X POST http://127.0.0.1/api/v1/notify/webpush/test \
  -H 'Content-Type: application/json' \
  -d '{"title":"Тест","body":"привет"}'
```

**Результат.** `{"ok":true,"result":[true,null]}` и тосты на подписанных устройствах.

### 4.2. Список подписчиков

**Команда:**

```bash
COMPOSE=(docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml)
"${COMPOSE[@]}" exec -T db psql -U "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_USER"')" \
  -d "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_DB"')" -Atc \
"SELECT endpoint, created_at FROM webpush_subscriptions ORDER BY created_at DESC LIMIT 10;"
```

### 4.3. Что работает автоматически (уже в коде)

- Пуши уходят с `urgency: high` — иначе iOS задерживает доставку.
- Подписки с ответом `410/404` (протухшие) удаляются сами при отправке.
- Apple периодически меняет endpoint подписки — sw.js сам переподписывается
  (событие `pushsubscriptionchange`) и присылает новую подписку на сервер.
- VAPID sub берётся только из настроек клуба / White-label — в коде нет
  ни одного «жёсткого» адреса.

### 4.4. Ротация ключей

**Действие.** Сгенерировать ключи заново (1.2), затем:

```bash
"${COMPOSE[@]}" exec -T db psql -U ... -Atc "DELETE FROM webpush_subscriptions;"
```

**Результат.** Все устройства переподписываются (часть 3).

---

## ЧАСТЬ 5. НЕИСПРАВНОСТИ

| Симптом | Причина | Решение |
|---|---|---|
| `403 BadJwtToken` (web.push.apple.com) | VAPID sub с нереальным доменом (.local и т.п.) | Заполнить «VAPID sub»: mailto:адрес@реальный-домен |
| `403 ... VAPID credentials do not correspond` | ключи перегенерированы, устройство подписано старым | `DELETE FROM webpush_subscriptions;` + на устройстве удалить данные сайта + подписка заново |
| `410 Gone` | подписка протухла | Переподписаться на устройстве (запись удалится сама) |
| `нет подписок` | никто не подписан | Часть 3 |
| `Cannot read properties of undefined (reading 'register')` | не secure context (http://&lt;IP&gt;) | HTTPS (часть 2) или localhost/portproxy |
| Страница «без web-push» | WebView/старый браузер | Системный Chrome (Android) или Safari (iOS) |
| `Could not deserialize key data` | ключ не в формате base64(DER) | П.1.2 заново |
| `sent:1`, тоста нет (Windows) | Windows глушит уведомления | Параметры → Система → Уведомления → Chrome вкл.; «Фокусировка внимания» выкл. |
| Пуш не приходит на iPhone при корректном всём | iOS держал низкий приоритет | Уже решено: urgency high; проверьте Focus/Не беспокоить и разрешения PWA |

---

## Примечания

- Конкретные значения (белые/LAN IP, пути, имена контейнеров) — из установки
  платформы конкретного вендора; сверяйтесь со своей инфраструктурой.
- Ручная публикация (~15 минут на клуб) — временный этап: в Roadmap
  автоматическое заведение поддоменов API платформой при регистрации клуба.
- Для клиентских массовых уведомлений основной канал — MAX (уведомления
  присылает мессенджер), web push — канал персонала и запасной.