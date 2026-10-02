# Диагностика и устранение проблем

## Сбор информации

| Что | Где |
|---|---|
| Логи API | `cd deploy && docker compose logs api --tail 100` |
| Логи desktop | `logs/client_*.log` (кнопка «Скопировать логи» в Помощи) |
| БД | `docker exec -i deploy-db-1 psql -U fitnexus_user -d fitnexus_ai -c "…"` |
| Health | `/health/`, `/ops/health`, `/metrics`, `/rbac/health` |

## Desktop

| Симптом | Причина | Решение |
|---|---|---|
| «Сервер не подключён» | API down/адрес | `/health/`, «Подключения» |
| 401 в цикле | истёк токен | повторный вход; E70 сам обновит по saved_login |
| «Не удалось загрузить экран» | ошибка инициализации | запуск `python main.py` из консоли → traceback |
| Старая версия после сборки | старый exe / spec с относительными путями | запускать `dist\FitIntelDesktop.exe` (проверить LastWriteTime); spec — абсолютные пути; проверить, что не запущена установленная копия из Program Files |
| `'ApiClient' object has no attribute '_e55_*'` | старый client.py | setattr-цикл в конце E55_EXT (релиз 1.5.3) |
| push rejected: large files | dist/build/installer_out в git | `.gitignore`, `git reset --mixed <последний запушенный>` |
| push rejected: non-fast-forward | расхождение историй | `git pull --rebase origin main` |
| Пустое меню у пользователя | строгая модель ui_config: роли нет в ui_role_screens | «Экраны ролей» → отметить экраны; `/ui-config/my` |
| «Вечный круг» смены пароля superadmin | is_first_login не сброшен | `/auth/change-password` делает UPSERT license_state (релиз 1.5.3) |

## Касса и деньги

| Симптом | Причина | Решение |
|---|---|---|
| 400 «Смена закрыта» | чек при закрытой смене | «🔓 Открыть смену» |
| Баланс 0.00 после подтверждения | completed_at < opened_at (платёж создан раньше смены) | новые платежи в открытой смене |
| 502 «Касса недоступна» | dto_url/сеть | «⚙ Настройки кассы», ping ККТ |
| 502 «Касса вернула ошибку: N» | mock в старом состоянии / отказ ККТ | перезапуск mock; журнал ККТ |
| 403 «Снятие кассы» | роль | admin/бухгалтер |
| Проводки не появляются | ошибка вставки | traceback в логах api от `_create_accounting_entry`; `\d accounting_entries` |
| Webhook ЮKassa 401 | подпись | `YOOKASSA_WEBHOOK_SECRET` на сервере = в кабинете ЮKassa |
| Дубли от webhook | идемпотентность по event_key | проверить `yookassa_webhook_events` |
| Дайджест не приходит | email выкл/время | `/notify/settings`, digest_time, SMTP-тест |

## Сервер и инфраструктура

| Симптом | Решение |
|---|---|
| Медленные запросы face/отчёты (10–60 с) | BLAS-лимиты: `OPENBLAS/OMP/MKL_NUM_THREADS=1` (есть в compose.prod) |
| «No services to build» в prod | prod берёт готовый образ: собрать через test-compose и `docker tag fitintel:test fitintel:prod` + `docker save | gzip` |
| БД «role does not exist» | не `postgres`: см. `POSTGRES_USER` в compose (fitnexus_user) |
| pg_dump пустой/ошибка | пользователь/хост: `pg_dump -h 127.0.0.1 -U …`; fallback — каталог-дамп |
| API падает при старте | логи; часто миграции — `alembic upgrade head` (подсказка в `/setup/database/init`) |
| Место на диске | ротация `deploy/backups`, `exports/`, `uploads/chat` (>10 МБ файлы отклоняются) |
| Репликация | single-node — штатно; HA по ТЗ §9 |

## Интеграции

| Симптом | Решение |
|---|---|
| 1С: синхронизация 0 записей | тест связи (логин/пароль, роли в 1С), пути API V3, журнал `connector_sync_log` |
| CRM «ХИТ» — ошибка «требуется документация» | штатно: stub до получения спецификации от B-Office |
| Telegram 429 | rate-limit 30/сек — пауза |
| MAX не шлёт | bot_token в «Интеграции» (max_messenger), `/messenger/max/sync` |
| QR «Подпись недействительна» | `QR_SECRET_KEY` на сервере, TTL, device binding |

| 429 от nginx (не от API) | rate-limit: API 10 r/s, auth 5/мин | тюнинг nginx.conf |
| Grafana не пускает | admin/admin по умолчанию | сменить через GF_SECURITY_ADMIN_PASSWORD |
| Алерты не приходят | Alertmanager receiver "null" | настроить receiver (email/webhook) в alertmanager.yml |
| backup.ps1 не работает на Linux | это Windows-скрипт | на проде — volume ./backups + /ops/backup/run |
| dev-compose не поднимается | жёстко задан пароль БД в docker-compose.dev.yml | сменить, не использовать для прода |
| HTTP 423 | аккаунт заблокирован (5 попыток) | подождать 5 мин; admin — сбросить |
| Кэш доступа пропускает уволенного | кэш TTL 24 ч | /ops → инвалидация кэша по клиенту |

## Эскалация

Помощь → Поддержка (MAX): приложить логи (кнопка), описать: экран → кнопка → ожидалось/получено. Для инцидентов с кассой — также номер чека/смены и время.
