# FitIntel Platform (веб-панель платформенного администратора)

Этап A (данный каркас): WireGuard-сервер + Nginx с mTLS + platform_db (PostgreSQL).
Этапы Б–Е: API платформы, License Studio API, веб-панель, impersonation, аудит.

## Запуск (домашний сервер 192.168.101.125)

1. `cp .env.example .env` → заполнить пароль БД.
2. `bash scripts/gen_certs.sh ваш@email` → сертификаты в `nginx/certs/`.
   Импортируйте `client_ваш@email.p12` в браузер/ОС (это ваш mTLS-пропуск).
3. `docker compose up -d`
4. Проверка: `curl -k https://127.0.0.1:8443/health` (снаружи — с клиентским сертификатом).

## Проброс портов (роутер)

- TCP `8443` → `192.168.101.125:8443` (панель)
- UDP `51820` → `192.168.101.125:51820` (WireGuard, клубы подключаются к вам)

## Добавить клуб (после этапа Б)

1. В `wireguard_config/peerX/` забрать `peerX.conf` → отдать клубу.
2. Клуб: `wg-quick up ./peerX.conf` (PersistentKeepalive=25 уже в конфиге).
3. Клуб в platform_db: `INSERT INTO clubs (name, slug, wireguard_ip) VALUES (...)`.

## Отзыв сертификата админа

1. `openssl ca -revoke nginx/certs/client_EMAIL.crt -config ...`
2. Перегенерировать `ca.crl`, перезапустить nginx.
