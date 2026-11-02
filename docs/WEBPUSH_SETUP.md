# Web Push — настройка уведомлений (FitIntel Pro)

Уведомления из FitIntel в браузер сотрудника (Chrome/Edge), доходят до Windows
даже при свёрнутом браузере. Desktop-приложение не требуется.

Цепочка: сервер (VAPID-ключи) -> страница подписки -> браузер подписывается ->
сервер отправляет -> push-сервис браузера -> тост Windows.
У каждого сервера (клуба) СВОЯ пара ключей.

## Требования

- Сервер FitIntel с образом, включающим pywebpush (в main с 31.10.2026).
- ПК сотрудника: Chrome или Edge, Windows 10/11.
- Secure context для подписки: localhost или https:// (см. Шаг 2).

## Шаг 1. Сервер: генерация VAPID-ключей (один раз)

```bash
sudo -i
cd /opt/fitintel-pro              # на nfs: /home/andrei/fitintel-pro
COMPOSE=(docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml)

"${COMPOSE[@]}" exec -T api python - <<'PY'
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from sqlalchemy import text
from app.db.session import engine
import base64

sk = ec.generate_private_key(ec.SECP256R1())
der = sk.private_bytes(serialization.Encoding.DER,
    serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
priv_b64 = base64.urlsafe_b64encode(der).rstrip(b'=').decode()
pub_raw = sk.public_key().public_bytes(serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint)
pub = base64.urlsafe_b64encode(pub_raw).rstrip(b'=').decode()

from py_vapid import Vapid
Vapid.from_string(private_key=priv_b64)   # проверка формата

with engine.begin() as c:
    c.execute(text("UPDATE notification_settings SET webpush_enabled=true, "
        "vapid_private=:p, vapid_public=:u, updated_at=NOW() WHERE id=1"),
        {"p": priv_b64, "u": pub})
print('KEYS_OK=1')
PY
```

Проверка (ожидается `t|t`):

```bash
"${COMPOSE[@]}" exec -T db psql -U "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_USER"')" \
  -d "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_DB"')" -Atc \
"SELECT webpush_enabled, vapid_public IS NOT NULL FROM notification_settings WHERE id=1;"
```

Контакт VAPID подставляется автоматически из
«Параметры клуба → Настройки приложения → Email поддержки».

## Шаг 2. ПК сотрудника: secure context

**Вариант А (прод):** белый адрес + домен + HTTPS (Let's Encrypt в nginx).
Открывать `https://<домен>/api/v1/notify/webpush/page`.

**Вариант Б (проверка в локальной сети):** portproxy, CMD **от администратора**:

```bat
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=127.0.0.1 connectport=80 connectaddress=192.168.101.14
netsh interface portproxy show all
```

Открывать `http://localhost:8080/...` (localhost — безопасный контекст).
Убрать переброску: `netsh interface portproxy delete v4tov4 listenport=8080 listenaddress=127.0.0.1`.

## Шаг 3. Подписка в браузере

1. Открыть страницу (см. Шаг 2).
2. **«Подписаться»** → разрешить уведомления → «Подписка сохранена».
3. Повторить на каждом ПК-получателе.

## Шаг 4. Тестовая отправка (на сервере)

```bash
curl -sS -X POST http://127.0.0.1/api/v1/notify/webpush/test \
  -H 'Content-Type: application/json' \
  -d '{"title":"FitIntel Pro","body":"Тест push!"}'
```

Ожидается: `{"ok":true,"result":[true,null]}` и тост Windows.

## Шаг 5. Список подписчиков

```bash
"${COMPOSE[@]}" exec -T db psql -U "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_USER"')" \
  -d "$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_DB"')" -Atc \
"SELECT endpoint, created_at FROM webpush_subscriptions ORDER BY created_at DESC LIMIT 10;"
```

## Неисправности

| Симптом | Причина | Решение |
|---|---|---|
| `Cannot read properties of undefined (reading 'register')` | `http://<IP>` без secure context | Шаг 2 |
| `Could not deserialize key data` | ключ не в формате base64(DER) | Шаг 1 заново |
| `403 VAPID credentials do not correspond` | ключи перегенерированы, браузер подписан старым | `DELETE FROM webpush_subscriptions;` + в браузере удалить данные сайта + подписка заново (Шаг 3) |
| `sent:1`, тоста нет | Windows глушит уведомления | Параметры Windows → Система → Уведомления → Chrome — вкл.; «Фокусировка внимания» — выкл. |
| `sent:0`, no subscriptions | нет подписчиков | Шаг 3 |

## Эксплуатация

- Рассылка: «Уведомления → Отправка» и автоматические рассылки → всем подписчикам сервера.
- **Ротация ключей:** выполнить Шаг 1 → `DELETE FROM webpush_subscriptions;` → всем подписчикам повторить Шаг 3.
- **Прод:** обязателен HTTPS (белый адрес клуба + Let's Encrypt).


## Подписки: ПК, Android, iOS (пошагово)

### Предварительные настройки клуба (вкладка «Уведомления → Web Push»)
1. Включить «Web Push».
2. **VAPID sub — обязательно**: `mailto:адрес@домен.клуба` (реальный, маршрутизируемый домен!)
   или `https://домен.клуба`. Если оставить пустым/`.local` — Apple отклонит пуши
   ошибкой **403 BadJwtToken** (проверено). Значение берётся также из «Email поддержки»
   (Коммерция → White-label), если поле VAPID sub пусто.
3. Ключи VAPID генерируются кнопкой один раз; при смене ключей все подписчики
   должны переподписаться.

### ПК (Windows/macOS/Linux) — персонал
1. Открыть в Chrome/Edge: `https://<адрес-клуба>/api/v1/notify/webpush/page`
2. «Подписаться» → разрешить уведомления.
3. Проверка: «Уведомления → Отправка» (webpush) → тост в системе.

### Android — клиент/персонал
1. Chrome на телефоне: тот же URL `https://<адрес-клуба>/api/v1/notify/webpush/page`.
2. «Подписаться» → разрешить. Всё — пуши приходят из любой сети (доставку делает Google).

### iOS (iPhone/iPad) — только через PWA, имя = название клуба
Ограничение Apple: веб-пуш работает только из установленного на «Экран Домой»
веб-приложения (iOS 16.4+). Иконка и имя приложения — **название клуба** из
«Коммерция → White-label» (манифест PWA).
1. **Safari** (не Chrome, не MAX): открыть `https://<адрес-клуба>/api/v1/notify/webpush/page`.
2. «Поделиться» (квадрат со стрелкой) → «На экран Домой» → «Добавить».
   На рабочем столе появится иконка с именем клуба.
3. Запустить **с этой иконки** (откроется без адресной строки) → «Подписаться» →
   разрешить уведомления → «Подписка сохранена».
4. Проверка: отправка webpush → баннер на iPhone, даже когда приложение свёрнуто.

### Требование к адресу клуба
Страница подписки должна открываться по **HTTPS с доверенным сертификатом**
(иначе браузер не даст подписаться). Варианты: поддомен через платформу
(`<клуб>.fixintel.ru` → прокси на клуб, сертификат Let's Encrypt на платформе)
или собственный белый адрес клуба + свой сертификат.

### Эксплуатация (автоматика уже в коде)
- Пуши уходят с `urgency: high` (иначе iOS задерживает доставку).
- Подписки с ответом 410/404 (протухшие) удаляются автоматически при отправке.
- Apple периодически меняет endpoint подписки — sw.js сам переподписывается
  (событие `pushsubscriptionchange`) и отправляет новую подписку на сервер.
- Тест рассылки всем подписчикам:
  `curl -X POST http://127.0.0.1/api/v1/notify/webpush/test -H 'Content-Type: application/json' -d '{"title":"Тест","body":"привет"}'`

### Типичные ошибки в ответе `/webpush/test`
| Симптом | Причина | Решение |
|---|---|---|
| `403 BadJwtToken` (web.push.apple.com) | VAPID sub с нереальным доменом (.local и т.п.) | Заполнить VAPID sub (mailto:адрес@реальный-домен) |
| `410 Gone` | Подписка протухла (браузер удалил/переустановили ОС) | Переподписаться на устройстве; запись удалится сама |
| `нет подписок` | Никто не подписан | Подписаться со страницы |
| Страница «без web-push» в браузере | WebView/старый браузер | Открыть в системном Chrome/Safari |
