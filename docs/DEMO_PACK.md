# FitIntel Pro — полный демо-пакет (сборка 08.11.2026, v2)

Автономный стенд для демонстраций: образ api + клон БД + исходники + секреты +
автоустановщик (12 шагов) + самоподдерживающаяся статистика.
Хранить на 125: `/home/andrei/demo-pack/` (владелец root, права 700 — внутри ПДн и секреты!).

## Состав

| Файл | Что это |
|---|---|
| `fitintel-prod-CURRENT.tar.gz` | Docker-образ api/celery (текущий боевой) |
| `fitintel-db-YYYYMMDD-HHMMSS.dump` | pg_dump клона БД (клиенты, настройки, лицензия) |
| `env-clone.txt` | deploy/.env боевого стенда |
| `media_master_key` | секрет шифрования медиа |
| `media-*.tar.gz` | медиа-файлы (фото) |
| `fitintel-pro_src.tar.gz` | исходники проекта (без .git) |
| `demo-install.sh` | автоустановщик: свежая Ubuntu → рабочий стенд ~10 минут |
| `demo-boot.sh` | обновление статистики при загрузке VM |
| `SHA256SUMS.txt` | контрольные суммы |

## Развёртывание на любом ноутбуке (VM Ubuntu)

1. Скопировать папку пакета внутрь VM (shared folder / scp / флешка).
2. `sudo ./demo-install.sh` — Docker, volumes, образ, БД, медиа, mDNS, LT-клиенты,
   статистика за 60 дней, автообновление при загрузке VM — всё само.
3. Маркеры: `HEALTH=200`, `CLIENTS>0`, в конце шага 11 — `FILL_DONE visits≈9000 payments≈1800`.
4. Десктоп на Windows-хосте: `http://fitintel.local`, вход — учётка админа с боевого стенда.

## Как это живёт дальше (ничего не делать не надо)

- **При включении VM** systemd (demo-fill.service) сам ждёт стенд и подливает статистику
  за последние 7 дней → Главная, тепловая карта и ML всегда свежие, в любой день демо.
- **Живой поток клиентов** во время показа (визуально «Входы/Выходы», «Кто в зале»):
  ```bash
  cd fitintel-demo && docker cp tools/demo/demo_flow.py deploy-api-1:/tmp/flow.py
  docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec -T api     env PYTHONPATH=/app python /tmp/flow.py --target 25 --interval 15
  ```
  Ctrl+C — остановка; LT-клиенты фейковые, реальным людям ничего не уходит.
- **Перед крупным демо** (раз в пару месяцев): внутри api `python /tmp/fill.py --days 60 --per-day 140`.

## Если вход 401

Сброс пароля SuperAdmin хешем из контейнера api (подставьте свой пароль):
```bash
cd fitintel-demo
CID=$(docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml ps -q db)
DB_USER=$(grep '^POSTGRES_USER=' deploy/.env | cut -d= -f2-); DB_NAME=$(grep '^POSTGRES_DB=' deploy/.env | cut -d= -f2-)
HASH=$(docker exec deploy-api-1 python -c "from app.core.security import get_password_hash; print(get_password_hash('НОВЫЙ_ПАРОЛЬ'))")
docker exec "$CID" psql -U "$DB_USER" -d "$DB_NAME" -c "UPDATE users SET password_hash='$HASH', failed_login_count=0, locked_until=NULL WHERE lower(username) LIKE '%super%';"
```
Логин в desktop — строчными `superadmin`.

## Освежение пакета (перед важным показом)

На nfs: `docker save fitintel:prod | gzip > fitintel-prod-CURRENT.tar.gz`, свежий pg_dump,
пересобрать архив (`sha256sum * > SHA256SUMS.txt; tar czf demo-pack-full.tar.gz demo-pack`),
перезалить на 125.

## Безопасность

Пакет = ПДн клиентов (152-ФЗ) + секреты: права 700/600, не раздавать, не коммитить,
после демо на чужих площадках удалять копии.
