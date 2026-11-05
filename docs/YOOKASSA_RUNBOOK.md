# ЮKassa: пополнение кошелька в мини-приложении MAX — runbook «5 минут при появлении кабинета»

Код: `app/services/yookassa_service.py` (создание платежа), `app/api/v1/yookassa.py`
(webhook), `app/api/v1/miniapp_config.py` (topup). Подробный старый обзор: `docs/Docs_MAX_miniapp_YooKassa.md`.

## Что уже работает в коде (подготовлено 05.11)
- Платёж создаётся реальным API `api.yookassa.ru/v3/payments`: Basic Auth shopId:secret,
  Idempotence-Key, `confirmation.type=redirect`, `capture=true`, metadata `wallet_topup`/`client_id`/`bonus_percent`.
- Webhook `POST /api/v1/yookassa/webhook`: подлинность — по IP-диапазонам ЮKassa
  (185.71.76.0/27, 185.71.77.0/27, 77.75.154.0/23, 77.75.156.0/23, 2a02:5180::/32;
  оверрайд параметром `YK_WEBHOOK_ALLOW_IPS`, список через запятую) + ОБЯЗАТЕЛЬНАЯ сверка
  статуса платежа через API ЮKassa перед зачислением денег (спуф исключён). Реальный IP берётся
  из X-Forwarded-For/X-Real-IP (за nginx). Зачисление идемпотентно (event_key).
  Не подтверждённое событие -> HTTP 202, ЮKassa повторит уведомление.
- `return_url`: параметр `WALLET_RETURN_URL` -> Origin запроса -> дефолт.
- Без кабинета: `WALLET_PAY_PROVIDER=test` — мгновенное зачисление (эмуляция для демо).

## Шаг 1. Кабинет ЮKassa (тестовый — без договора и данных компании)
yookassa.ru -> регистрация -> раздел «Для интеграции»: скопировать shopId и секретный ключ.

## Шаг 2. Параметры клуба (Desktop -> Настройки -> Параметры клуба, двойной клик по строке)
| Параметр | Значение |
|---|---|
| WALLET_PAY_PROVIDER | `yookassa` |
| YK_SHOP_ID | shopId |
| YK_SECRET_KEY | секретный ключ |
| WALLET_RETURN_URL | (опц.) куда вернуть клиента после оплаты; пусто = Origin |

Кэш параметров ~60 сек, перезапуск не нужен.

## Шаг 3. Webhook в кабинете ЮKassa
URL: `https://<внешний-домен>/api/v1/yookassa/webhook` (HTTPS обязателен).
Проверка: `curl -s -X POST https://<домен>/api/v1/yookassa/webhook -H 'Content-Type: application/json' -d '{}'`
-> ожидается **403** (источник не из сетей ЮKassa = endpoint жив, фильтр работает).

## Шаг 4. Тестовый платёж
Мини-приложение -> «Пополнить баланс» -> 100 ₽ -> форма ЮKassa -> тестовая карта
`5555 5555 5555 4444` (любой CVC, дата из будущего) -> баланс +105 ₽ (бонус 5%),
сообщение «Кошелёк пополнен» в MAX. Не оплатил -> payment.canceled, деньги не зачисляются.

## Шаг 5. Боевой режим
Договор с ЮKassa -> боевые shopId/secret в те же параметры (переключатель test/live в кабинете).
Фискализация 54-ФЗ (ОФД) — отдельный блок Roadmap (A2).

## Диагностика
```bash
docker logs deploy-api-1 --since 10m | grep -iE 'yookassa|webhook'
docker exec deploy-api-1 python -c "
from app.api.v1.club_params import get_param
from app.db.session import SessionLocal
from app.services.yookassa_service import YooKassaService
print('provider =', get_param('WALLET_PAY_PROVIDER',''), '| enabled =', YooKassaService(SessionLocal()).enabled)"
```
| Симптом | Причина | Решение |
|---|---|---|
| Баланс растёт мгновенно, формы нет | WALLET_PAY_PROVIDER=test | шаг 2 |
| «Пополнить» молча ничего не делает | нет ключей, enabled=False | шаг 2 |
| HTTP 401 от api.yookassa.ru | неверная пара shopId/secret или режим test/live | проверить пару в кабинете |
| Оплата прошла, баланс не вырос | webhook не дошёл: URL не настроен / не HTTPS / недоступен снаружи | шаг 3 |
| Webhook стабильно 403 | сменились IP ЮKassa или свой прокси | параметр YK_WEBHOOK_ALLOW_IPS |

## Безопасность
Секретный ключ хранится в club_params открытым текстом (виден суперадмину в UI) —
хвост общей темы шифрования секретов параметров клуба. В git/логи не попадает.
