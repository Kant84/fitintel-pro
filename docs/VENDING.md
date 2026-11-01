# Vending API — контракт для интеграции автоматов (FitIntel Pro)

Клиент платит за товары автомата **с баланса кошелька** клуба.
Два канала идентификации клиента: RFID-браслет (uid) и код с экрана
(клиент вводит его в мини-приложении MAX). Деньги — не карта и не наличные
в автомате, а баланс FitIntel: списание на сервере, возврат при сбое выдачи.

## Авторизация автомата

Все машинные запросы — с заголовком:

    X-Device-Token: <api_token устройства>

Устройство создаётся администратором сервера:

    INSERT INTO vending_devices (id, name, api_token, location)
    VALUES (gen_random_uuid(), 'Автомат 1', '<случайный токен 32+ символа>', 'Холл');

## Канал 1 — RFID-браслет (приложил — списалось)

    POST /api/v1/vending/purchase
    {"uid": "<RFID uid браслета>", "product_name": "Вода 0.5", "price": 50}
    -> {"allow": true, "sale_id": "...", "balance_after": "450.00"}
    -> {"allow": false, "reason": "Недостаточно средств..."}

## Канал 2 — код с экрана (оплата из миниаппа MAX)

1. Автомат (клиент выбрал товар на экране):

       POST /api/v1/vending/session
       {"product_name": "Кофе", "price": 120}
       -> {"code": "890898", "qr_text": "890898", "session_id": "..."}

   На экране показывается 6-значный код (и QR с ним для авто-ввода).
   Сессия живёт 10 минут.

2. Клиент в миниаппе: «Оплата на автомате» -> вводит код -> списание
   (авторизация Bearer-токеном миниаппа):

       POST /api/v1/vending/pay
       Authorization: Bearer <токен клиента>
       {"code": "890898"}
       -> {"ok": true, "product": "Кофе", "price": "120.00",
           "balance_after": "330.00", "sale_id": "..."}

3. Автомат опрашивает (раз в 1-2 секунды):

       GET /api/v1/vending/session/890898
       -> {"status": "OPEN" | "PAID", "product": ..., "price": ...,
           "client_label": ..., "sale_id": "...", "expires_at": ...}

   При status=PAID -> выдать товар.

## Подтверждение выдачи (обязательно после выдачи или сбоя)

    POST /api/v1/vending/confirm
    {"sale_id": "...", "status": "dispensed"}   # товар выдан
    {"sale_id": "...", "status": "failed"}      # сбой -> автовозврат на баланс
    -> {"ok": true, "status": "CONFIRMED" | "REFUNDED"}

## Журнал продаж автомата

    GET /api/v1/vending/sales?limit=50
    -> {"items": [{id, client_label, product_name, price, status, created_at}]}

Статусы продажи: PENDING -> PAID -> CONFIRMED | REFUNDED; DECLINED — отказ
(не хватило средств). Таблицы: vending_devices, vending_sales, vending_sessions.

## Примечания для MDB-адаптера (прошивка контроллера автомата)

- Сессия MDB "VEND" мапится на POST /purchase (RFID-ридер на автомате) или
  на пару /session + опрос (оплата из приложения).
- До выдачи дождитесь allow:true / status=PAID; после выдачи/сбоя всегда
  вызывайте /confirm — иначе продажа останется в PAID.
- Недостаток средств -> покажите клиенту подсказку пополнить баланс
  (reason из ответа содержит доступный остаток).
- Эмулятор для стенда: tools/mock_vending.py (команды purchase/session/poll/confirm/sales).
