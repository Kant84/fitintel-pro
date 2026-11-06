# server — сервер клуба (кратко; полное руководство — INSTALL_SERVER.md)

> Категория: server · Проверено для: 1.6.2 · Для кого: IT клуба, администратор.

## Требования к серверу
Ключевые слова: требования сервер, железо, vcpu, ram
**Ответ.** Минимум: 2 vCPU / 4 ГБ RAM / 40 ГБ SSD, Ubuntu 22.04/24.04, Docker 24+. Рекомендуется: 4 vCPU / 8 ГБ / 80 ГБ. Порты: 80 (клиенты), 22 (SSH, только доверенная сеть). Подробно — INSTALL_SERVER.md §1.
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Установка сервера с нуля (кратко)
Ключевые слова: установка сервера, с нуля, install_prod
**Ответ.** 5 шагов: 1) `sudo apt update && sudo apt install -y ca-certificates curl git python3`; 2) Docker Engine + Compose (INSTALL_SERVER.md §2); 3) `sudo git clone https://github.com/Kant84/fitintel-pro.git /opt/fitintel-pro`; 4) `cd /opt/fitintel-pro && sudo bash deploy/install_prod.sh`; 5) создать администратора (скрытый ввод, пароль ≥ 12 символов). ПОЛНОЕ руководство с разбором ошибок — INSTALL_SERVER.md (главный документ).
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Проверка: всё ли работает после установки/обновления
Ключевые слова: проверка установки, health, контейнеры up
**Ответ.** `docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml ps` — db healthy, api/nginx/celery Up. Затем: `curl http://<IP>/api/v1/health/` → `{"status":"ok",...}`. Помните: сразу после `up -d` возможен 502 на 20–30 секунд (прогрев) — подождите и повторите (INSTALL_SERVER.md §9).
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Обновление сервера
Ключевые слова: обновить сервер, git pull, новая версия
**Ответ.** `sudo git -C /opt/fitintel-pro pull --ff-only` → пересборка образа → `alembic upgrade head` → `up -d` → проверка health через 20 секунд. По шагам и с ошибками — INSTALL_SERVER.md §13. Установщик поверх действующего клуба не запускается.
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Бэкапы: настроить и проверить
Ключевые слова: бэкап, резервная копия, install_cron, восстановление
**Ответ.** Настройка одной командой: `sudo bash /opt/fitintel-pro/deploy/backup/install_cron.sh` — ежедневно ~21:30, архивы `fitintel_full_*.tar.gz` (БД + файлы + .env + лицензия), ротация 14 дней, права 0600. Проверка: `systemctl list-timers fitintel-backup.timer`. Восстановление — INSTALL_SERVER.md §12. Раз в месяц делайте restore-test на отдельном стенде.
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Ротация пароля СКУД (ITC) — три точки
Ключевые слова: ротация itc, сменить пароль турникета, itc_basic_password
**Ответ.** Один пароль в трёх местах: 1) `deploy/.env` (`ITC_BASIC_PASSWORD`) → `docker compose up -d --force-recreate api`; 2) реестр ITCService (BasicAuthPass) → `Restart-Service ITCService`; 3) `/etc/fitintel/bridge.env` (itc_password) → `systemctl restart ent_bridge`. Проверка: старый пароль → 401, новый → 422. Подробно — ITCService_SETUP.md §«Безопасность».
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Место на диске заканчивается
Ключевые слова: место на диске, диск заполнен, df
**Ответ.** `df -h` и `docker system df`. Ротация бэкапов 14 дней уже есть; очистка: `docker system prune`. Настроен алерт DiskSpaceLow в мониторинге (INSTALL_SERVER.md §16 п.7).
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Доступ к каталогу сервера и права
Ключевые слова: sudo, права 750, доступ к /opt/fitintel-pro, secure_install
**Ответ.** Каталог принадлежит root: работа только через `sudo -s`. Рекомендуемое ужесточение: `sudo bash scripts/secure_install.sh` (права 750/640/600, группа admin.platform, проверка членов docker) → маркер `SECURE_OK=1`. `chmod 777` не применять (INSTALL_SERVER.md §8).
**Если не помогло:** «Помощь → Поддержка разработчика (MAX)».

## Когда звать разработчика, а когда — IT клуба
Ключевые слова: кто чинит, it клуба или поддержка, ответственность
**Ответ.** IT клуба: сеть, Windows, принтеры, камеры, кассовое ПО ККТ, регистрация ФН/ОФД, 1С. Поддержка разработчика (FitIntel): ошибки ПО, 5xx от API, webhook'и, лицензии, интеграции FitIntel. Граница: если `curl http://<IP>/api/v1/health/` не возвращает `{"status":"ok"}` — сначала IT клуба по INSTALL_SERVER.md, потом поддержка (ИНСТРУКЦИЯ §48).
**Если не помогло:** —
