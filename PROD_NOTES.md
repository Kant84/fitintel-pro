# PROD_NOTES.md — что важно помнить перед продом

## Общее / безопасность
- `.env` попадал в git-историю — секреты (пароли БД, SECRET_KEY) считать скомпрометированными, перед продом ротировать.
- Face ID — только self-hosted (без FindFace/NtechLab/Face++): лицензии + 152-ФЗ.
- WebSocket/подключения — только 127.0.0.1 (IPv6 ::1 заблокирован на машине разработки).

## E22 Online Training
- E22.9/10: запись сессий логическая (метаданные в БД), реального медиасервера нет.
- E22.13: endpoint /online-sessions/reminders/run готов, нужен планировщик (apscheduler/cron).
- E22.14/15: ссылки Zoom/Google Meet генерируются фабрикой; боевые API — после добавления ключей.

## E23 Hardware
- E23.13–15: работа через DeviceProtocolEmulator (modbus_tcp/http_api/mqtt); боевые контроллеры — заменить эмулятор на драйверы.

## E24 Messenger
- E24.15: push — точка интеграции FCM (заглушка {"channel": "fcm"}).

## E25 Telegram Bot / MAX Bot
- Отправка сообщений идёт в боевой API только при настроенных токенах (TelegramSettings / MaxBotSettings в БД).
- /cron/subscription-expiry и /cron/booking-reminder — готовы к подключению к планировщику.

## E26 YooKassa
- Реальные ключи YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY в .env — и модуль переключится с эмуляции на боевой API (yookassa_service.py уже умеет ходить в api.yookassa.ru).
- Для международных платежей архитектура готова: поле payment_system в payments — добавить Stripe/CloudPayments = ещё один роутер рядом с /yookassa.
- Переключатель /yookassa/test/simulate — только для тестов, в проде отключить (или оставить — он под авторизацией).
- Подпись webhook: у боевой YooKassa проверка по IP-списку; наш HMAC (X-YooKassa-Signature) — дополнительная защита endpoint'а, в проде комбинировать оба подхода.
- E26.12/13: эмуляция сбоев через переключатель; реальные 503/504 от api.yookassa.ru обрабатываются тем же кодом через try/except в _api() сервиса.
- E26.9/10: рекуррент — реальный автоплатёж требует save_payment_method: true при первом платеже и списание по payment_method_id; логика списания готова, боевой вызов API — одна строчка при появлении ключей.


## E29 Phone Verify
- `dev_code` в ответе /phone-verify/send — ТОЛЬКО для тестов; в проде убрать из ответа (код должен уходить только в SMS/мессенджер).
- Провайдеры smsru/twilio/whatsapp/telegram — эмуляция. Боевые интеграции: ключи SMSRU_API_KEY, TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN, WhatsApp Business API; отправка через telegram — по telegram_links (E25).
- /phone-verify/test/providers — тестовый переключатель сбоев, в проде отключить.
- Rate-limit (5 попыток/15 мин, resend 1/мин) — в БД/памяти; в проде при нескольких инстансах вынести в Redis.
- TTL кода 5 мин; верификация при регистрации: register сохраняет phone, /verify ставит users.phone_verified=true.

## E28 License
- License server — локальная эмуляция (POST /license/generate выдаёт ключи FITI-XXXXXXXX-CCCC с HMAC-контрольной суммой). В проде ключи выдаёт внешний вендор-сервер; HMAC-подпись лицензии стоит заменить на асимметричную (Ed25519): публичный ключ зашит в код, приватный у вендора.
- Лицензия живёт в существующей таблице licenses (модель face_id.License), добавлены колонки device_limit/grace_days/offline_days/last_check/plan. Legacy-эндпоинты /license/verify|limits|revoke|activations сохранены со старой заглушкой авторизации — в проде перевести на реальную.
- Устройства — таблица license_devices (license_ref текстовый, т.к. id лицензии integer).
- E28.13/14: офлайн-режим проверяется по last_check в БД; реальная «работа без интернета» должна дополнительно гасить защищённые запросы через middleware.
- Секрет подписи: LICENSE_SECRET в .env (дефолт test-only).
