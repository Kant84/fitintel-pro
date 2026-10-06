# 📧 EMAIL_SETUP_GUIDE — настройка почты FitIntel Pro

> Дата: 06–07.10.2026 · Статус: применено в проде (клубный профиль — 8 писем SENT, системный — 1 письмо SENT)

## 1. Архитектура: два независимых профиля SMTP

| Профиль | Кто | Зачем | Где настраивается |
|---|---|---|---|
| `club` (по умолчанию) | Почта **клуба** | Рассылки клиентам, тестовые письма, дайджест | Desktop → «Уведомления» → Email (пишется в БД, `notification_settings`) |
| `system` | Почта **разработчика** (support@fixintel.ru) | Алерты мониторинга, лицензии, поддержка клубов | env сервера: `SYSTEM_SMTP_*` |

Принцип: клуб не видит системный профиль и не может завалить ящик разработчика; мониторинг не зависит от настроек клуба.

**Поток письма (A4 — очередь):** отправка ВСЕГДДА через таблицу `email_queue` (статусы PENDING → SENT/FAILED, ретраи 1 → 5 → 15 мин, после 3 попыток FAILED). Нет «мгновенной отправки» — письмо копится и уходит процессингом.

## 2. Настройка клубного профиля (desktop)

1. «🔔 Уведомления» → подвкладка «📧 Email» → галочка «Включить Email-уведомления».
2. Поля:

| Поле | Пример | Примечание |
|---|---|---|
| SMTP хост | `smtp.mail.ru` / `smtp.yandex.ru` / `smtp.gmail.com` / `mail.vashdomen.ru` | Сервер **того почтовика, чей ящик в поле «логин»** |
| Порт | `465` (SSL) или `587` (TLS) | Рекомендуем 465 |
| Логин | полный адрес: `club@mail.ru` | |
| Пароль | см. таблицу ниже | ⚠️ главный источник ошибок |
| От кого | тот же полный адрес | |
| Время дайджеста | `09:00` | Ежедневная сводка клубу |

3. «💾 Сохранить Email» → подвкладка «📨 Отправка» → канал `email`, получатель = свой ящик → «📨 Отправить».

### Пароль: правило почтовика

| Почтовик | Что вписывать |
|---|---|
| mail.ru | **Пароль приложения** (Настройки аккаунта → Безопасность → Пароли приложений). Пароль ящика НЕ подойдёт — mail.ru вернёт `535 Application password is REQUIRED` |
| Yandex / Gmail | Пароль приложения (только при включённой 2FA) |
| Свой сервер (Mailcow и др.) | Обычный пароль ящика |

## 3. Настройка системного профиля (env сервера)

```env
SYSTEM_SMTP_HOST=mail.fixintel.ru
SYSTEM_SMTP_PORT=465
SYSTEM_SMTP_USER=support@fixintel.ru
SYSTEM_SMTP_PASSWORD=<пароль ящика support>
SYSTEM_SMTP_FROM=support@fixintel.ru
```
После изменения: `docker compose -f docker-compose.test.yml up -d --force-recreate api`.
Проверка: `docker exec deploy-api-1 python -c "from app.core.config import settings; print(settings.SYSTEM_SMTP_HOST, settings.SYSTEM_SMTP_USER)"`.

Отправка системного письма из кода: `NotificationService(db).send_system_email(кому, тема, текст)` → профиль `system`.

## 4. Просмотр писем: ушедших и застрявших

```bash
# Все письма очереди (свежие сверху):
docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c \
"SELECT recipient, subject, status, attempts, left(last_error,80) AS err, created_at, sent_at \
 FROM email_queue ORDER BY created_at DESC LIMIT 20;"

# Только застрявшие / упавшие:
docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c \
"SELECT recipient, status, attempts, last_error FROM email_queue WHERE status <> 'SENT' ORDER BY created_at DESC;"

# Журнал уведомлений (вкладка «Журнал» в desktop читает тот же источник):
docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c \
"SELECT channel, recipient, subject, status, error, created_at FROM notification_log ORDER BY id DESC LIMIT 20;"
```

**Статусы:** `PENDING` — ждёт (SMTP не настроен, либо backoff до ретрая); `SENT` — ушло; `FAILED` — 3 неудачных попытки, смотреть `last_error`.

## 5. Ручной процессинг (отправить накопленное немедленно)

```bash
docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c \
"UPDATE email_queue SET attempts=0, next_attempt_at=NULL WHERE status='PENDING';"
docker exec -w /app deploy-api-1 python -c "
from app.db.session import SessionLocal
from app.services.email_queue_service import EmailQueueService
print(EmailQueueService(SessionLocal()).process_queue())"
# ожидаем: {'processed': N, 'sent': N, 'failed': 0, ...}
```
Есть и endpoint: `POST /api/v1/email-queue/process` (админ, из UI «Журнал»/по кнопке).

## 6. Типовые ошибки и что делать

| Симптом (last_error / ответ) | Причина | Лечение |
|---|---|---|
| `535 ... Application password is REQUIRED` (mail.ru) | Вписан пароль ящика вместо пароля приложения | Создать пароль приложения (п.2) |
| `535 5.7.8 authentication failed` | Неверный пароль ИЛИ хост не принадлежит почтовику ящика | Проверить пароль через `doveadm auth test` на своём сервере; хост = сервис ящика |
| Письмо висит `PENDING`, ошибок нет | SMTP не заполнен в настройках | Заполнить и сохранить (п.2), затем процессинг |
| `waiting_smtp` в ответе process_queue | Те же — конфиг не читается | `SELECT smtp_host, smtp_user, length(smtp_pass) FROM notification_settings WHERE id=1;` |
| Timeout/нет соединения | Порт закрыт файрволом, не тот порт | 465 SSL / 587 TLS; проверить `openssl s_client -connect host:465` |
| Desktop: «localhost:8001» в ошибке | Старая версия вкладки «Уведомления» (исправлено cad7d63) | Обновить desktop из git, перезапустить |

## 7. Диагностика «в лоб» (проверка SMTP с сервера)

```bash
docker exec -i deploy-api-1 python - <<'EOF'
from app.db.session import SessionLocal
from sqlalchemy import text
import smtplib
db = SessionLocal()
host, port, user, pwd = db.execute(text(
    "SELECT smtp_host, smtp_port, smtp_user, smtp_pass FROM notification_settings WHERE id=1")).first()
print("connect:", host, port, user)
try:
    srv = smtplib.SMTP_SSL(host, int(port or 465), timeout=15)
    srv.login(user, pwd)
    print("AUTH OK")
    srv.quit()
except Exception as e:
    print("AUTH FAIL:", str(e)[:150])
EOF
```

## 8. Что было сделано по почте (06.10)

1. **Очередь `email_queue`** + `EmailQueueService` (ретраи 1→5→15 мин, FAILED после 3 попыток), миграция колонки `profile` в `ensure` (старые БД).
2. **Унификация схемы `notification_settings`** (колонки, не JSON) — исправлен конфликт двух схем.
3. **Два профиля SMTP** (`club` из БД / `system` из env) — `NotificationService.send_system_email()`.
4. Desktop: вкладка «Уведомления» переведена на настроенный API-клиент (был хардкод localhost); в F1 добавлена инструкция по настройке почты; «Помощь → Поддержка» — support@fixintel.ru.
5. **Mailcow владельца** (mail.fixintel.ru): ящики andrei@ и support@ работают; сброс пароля через `doveadm pw` + UPDATE mailbox; dockerapi кэширует хэш — после смены пароля `docker restart mailcowdockerized-dockerapi-mailcow-1`.
6. **Боевая проверка:** клубный профиль — 8 писем SENT (smtp.mail.ru → пароль приложения); системный — 1 письмо SENT от support@fixintel.ru.
7. Автотесты: `tests/test_email_queue.py` (4 теста) в общем наборе **59 passed**.

## 9. Как клубу обратиться в поддержку

**support@fixintel.ru** (также: Помощь → Поддержка разработчика в desktop). В письме: экран, кнопка, ожидание/факт, логи («Скопировать логи»).
