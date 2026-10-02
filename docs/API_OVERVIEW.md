# Обзор API (v1)

База `http://<сервер>:8001/api/v1`. Авторизация: `POST /auth/login` → Bearer. Desktop обновляет токен автоматически (E70).

## Группы endpoint'ов

| Группа | Пути | Примечания |
|---|---|---|
| Auth | `/auth/register|login|refresh|me|change-password|token-check|2fa/*|forgot-password` | superadmin: force_change_password при первом входе |
| Пользователи/RBAC | `/users/*` (CRUD, reset-password, roles assign/revoke, /roles, /permissions), `/roles/*`, `/permissions/*`, `/rbac/*` (matrix, check/explain/debug-access, health) | права users.read/create/update/delete, roles.manage |
| Клиенты | `/clients/*` | аудит crm.client.read |
| Абонементы | `/subscriptions/*` (+`/extend`), lifecycle: freeze/unfreeze/renew/cancel в сервисе, события в `subscription_events`; авто-истечение (Celery) | renew сдвигает end_date; freeze сдвигает при разморозке на frozen-дни |
| Тарифы | `/tariffs/*` (GET по code!) | валюта RUB, is_unlimited⇒visit_limit=null |
| Визиты | `/visits/*` (entry/exit/check-in/check-out/manual/auto-close/stats|today|week|month, /active, /active/count) | time_restriction FULLDAY/DAYTIME/NIGHTTIME; 409 при повторном входе |
| Платежи | `/payments/*`, `/wallet/*`, `/sales/*` | complete = чек; refund ≤ суммы |
| Касса | `/fiscal/open-shift|close-shift|cash-withdrawal|x-report|z-report|atol|shtrih|refund|correction|settings|shift|status|ofd-check`, `/cash-desk/*` | guard смены на сервере; settings — admin |
| Чеки | `/receipts/*` | номер/payment/number, send, pdf, ofd-status, fiscalize |
| Онлайн | `/yookassa/*` (payments/webhook/refunds/cards/auto-charge/test/simulate), `/recurring/*` (schedules/run/test) | идемпотентность webhook |
| Проводки/учёт | `/accounting/entries`, `/reporting/*` (payroll, 6ndfl(+export), rsv(+export), usn-declaration, calendar, summary) | 6-НДФЛ/РСВ XML |
| AI/аналитика | `/ai/churn/train|predict|resolve`, `/ai/status`, `/analytics/dashboard|forecast|recalc|heatmap`, `/analytics/ai/*` | предикт: «Модель не обучена» |
| Доступ | `/credentials/*` (qr/rfid/card/bracelet/mobile-key/online-lock/emulate/program/validate/force-write/reassign), `/dynamic-qr/*` (generate/validate/my/revoke/verify/guest/group/turnstile), `/face-id/*` (register/verify/turnstile/settings/templates/anti-spoofing/liveness/engine), `/lockers/*`, `/skud/*` (ITC Basic Auth), `/kerong/*`, `/visits` | QR: HMAC-SHA256, TTL, jti, device binding |
| Оборудование | `/devices/*`, `/dal/*` (repository/drivers/devices/events), `/rfid/*` | .fnp пакеты |
| Услуги/тренеры | `/services/*` (book/availability/trainer-schedule), `/trainers/*` (profiles/schedules/bookings/attendance/sales/dashboard/kpi) | отмена записи за 24 ч; KPI прогрессивный |
| Онлайн-тренировки | `/online-training/*`, `/online-sessions/*` | zoom/gmeet ссылки, напоминания, чат, screen-share, запись |
| Виджет записи | `/booking-widget/public/*` (config/services/slots/book/status/cancel), `/embed/{club}` | публичный, без JWT |
| Мессенджеры | `/messenger/*` (chats/messages/bindings/notify/broadcast/notifications/reminders/settings), `/max-bot/*` (+/fsm), `/telegram/*`, `/chat/*`, `/chats/*` (WS) | rate-limit 30/сек |
| Маркетинг | `/marketing/*` (segments, sms/email, campaigns + launch + analytics + roi + ab-test, providers) | кампании эмуляция метрик |
| Геймификация | `/gamification/*` | XP/уровни/достижения/лидерборд/награды |
| Рефералка | `/referrals/*` | антифрод: самоприглашение/дубль → 400/409 |
| Документы | `/documents/*`, `/document_templates/*`, `/documents_bulk/*` | шаблоны {{client_name}}… |
| Отчёты | `/reports/*` (operational/hourly/shifts), `/reporting/*`, `/sales/report`, `/exports/*` (jobs/quick), `/export/*` (E19: JWT-ссылки 24 ч, forget) | forget — анонимизация 152-ФЗ |
| Система | `/users`, `/audit/*` (+retention), `/ui-config/*` (screens/roles/my), `/feature-flags/*` (+rollout/license-bind/stats/stream), `/license/*`, `/setup/*` (мастер), `/ops/*` (backup/health/replication), `/health/`, `/metrics`, `/notifications` (SMTP/SMS/webpush/digest) | строгая модель экранов |
| Документы | `/documents` (CRUD, /sign, /sign-ep, /download?format=pdf\|docx, /send-email, /print), `/documents/mass-generate`, `/{id}/events|signatures|relations|history` | PDF/DOCX в коде |
| Коммерция | `/commercial/plans|subscribe|subscriptions/{club}/upgrade|features`, `/brand/settings|tenants|summary` | white-label, тенанты |
| Видео | `/video-ai/triggers|events|cameras` (+learn, confirm/false-alarm), `/video-alerts` (+/face-match) | feedback-loop дообучения |
| Self-learning | `/self-learn/pricing/*`, `/self-learn/self-heal`, `/self-learn/churn/*`, `/ml/predict/churn(+batch)`, `/ml/features/client`, `/auto/run-daily|stats` | |
| Телефон | `/phone-verify/send|verify|resend`, `/clients/verify-phone/request|confirm|status` | fallback провайдеров |
| Real-time/печать | `/sse/live/{club}`, `/ws/alerts`, `/feature-flags/stream`, `/print/*`, `/reader/*` | |
| Health | `/health/` (БД), `/ops/health` (БД+диск+память+бэкап) | |
| Прочее | `/aa/*`, `/integrations-config/*`, `/branding/*`, `/commercial/*` (white-label/tenants), `/wallet/*`, `/connectors` | tenants — сети клубов |

## Ответы и ошибки

Успех: 200/201 (+JSON; списки — массив или `{"items"|"entries"|...}`). Ошибки: `{"detail": "…"}`
- 400 бизнес (смена закрыта, лимит визитов, «Нельзя заморозить в статусе…», сумма возврата > платежа, неверный формат даты/телефона);
- 401 токен/подпись; 403 право/роль/участник чата/доступ запрещён (в т.ч. время тарифа, низкая уверенность Face ID);
- 404 не найдено; 409 конфликт (дубль, занят слот/шкафчик, уже в клубе, активный QR существует);
- 410 QR использован/истёк; 413 файл >10 МБ; 422 валидация; 429 rate-limit; 502 ККТ/внешний API; 503 устройство недоступно.

## Пример: платёж с чеком

```bash
B=http://localhost:8001/api/v1
tok=$(curl -s -X POST $B/auth/login -H 'Content-Type: application/json'   -d '{"login":"superadmin","password":"***"}' | jq -r .access_token)
curl -s -X POST $B/fiscal/open-shift -H "Authorization: Bearer $tok"
pid=$(curl -s -X POST $B/payments/ -H "Authorization: Bearer $tok" -H 'Content-Type: application/json'   -d '{"client_id":"…","amount":300,"payment_method":"CASH","payment_direction":"INCOMING"}' | jq -r .id)
curl -s -X POST $B/payments/$pid/complete -H "Authorization: Bearer $tok"   # чек здесь
curl -s $B/fiscal/shift -H "Authorization: Bearer $tok"
curl -s $B/accounting/entries -H "Authorization: Bearer $tok"
```
