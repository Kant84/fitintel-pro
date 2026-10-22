# FitIntel Platform — удалённый доступ: mTLS и WireGuard

Версия 1.0 (22.10.2026). Для администраторов и поддержки FitIntel Pro.
Связанные документы: `MTLS_PLATFORM_ACCESS.md` (mTLS-канал, сертификаты, файрвол),
`PLATFORM_DEPLOY_GUIDE.md` (развёртывание и эксплуатация платформы).

---

## 1. Два разных канала — не путать

| Канал | Кто | Что даёт | Что нужно клиенту |
|---|---|---|---|
| **mTLS по белому IP** (TCP 8443) | администраторы/поддержка | только веб-панель платформы | клиентский сертификат (.p12) в браузере/ОС |
| **WireGuard** (UDP 51820) | клубы и (опционально) админы | служебная подсеть 10.0.0.0/24: API платформы напрямую, SSH, БД, heartbeat клубов | файл туннеля .conf (или QR) |

- Панель из любой точки мира: `https://<ПУБЛИЧНЫЙ_IP>:8443/` — работает уже сейчас,
  WireGuard для этого **не нужен**.
- WireGuard — канал для **клубов** (heartbeat, будущий API-доступ платформы к клубу)
  и для полного доступа админов к серверу (SSH/БД) извне.

## 2. Адресное пространство туннеля

- Подсеть: `10.0.0.0/24` (задана в compose: INTERNAL_SUBNET).
- Сервер платформы: `10.0.0.1` (wg-интерфейс контейнера wireguard).
- Пиры: `10.0.0.2`, `10.0.0.3`, … (peer1, peer2, … — по одному на клуб/админа).
- `AllowedIPs = 10.0.0.0/24` у пиров: туннель несёт только служебный трафик,
  обычный интернет-трафик клиента не заворачивается.

## 3. Выдача доступа АДМИНИСТРАТОРУ (сценарий)

### 3.1 На сервере платформы

```bash
cd ~/fitintel-pro/deploy/platform
# увеличить число пиров (образ linuxserver/wireguard догенерирует новые)
sed -i 's/PEERS: "10"/PEERS: "11"/' docker-compose.yml   # подставьте актуальное число+1
docker compose up -d
docker compose exec wireguard ls /config | grep peer
# забрать конфиг нового пира (~20 строк, копируем вывод целиком):
docker compose exec wireguard cat /config/peer11/peer11.conf
```

### 3.2 На устройстве админа

1. Установить клиент: https://www.wireguard.com/install/ (Windows/macOS/Linux/Android/iOS).
2. WireGuard → «Импорт туннеля из буфера обмена» → вставить скопированный конфиг →
   сохранить → **Активировать**.
3. Проверка: `ping 10.0.0.1`.

### 3.3 Проверка на сервере

```bash
docker compose exec wireguard wg show
# peer11: latest handshake — секунды назад, transfer растёт — туннель жив
```

### 3.4 Что доступно админу по туннелю

| Ресурс | Адрес |
|---|---|
| Панель | `https://10.0.0.1:8443/` (браузер спросит сертификат как обычно) |
| API платформы напрямую | `http://10.0.0.1:8002/platform/clubs` |
| SSH | `ssh andrei@10.0.0.1` |
| PostgreSQL (отладка) | `psql -h 10.0.0.1 -p 5433 -U platform_user platform` |

> Нюанс: в серверном сертификате нет SAN `10.0.0.1` → браузер покажет предупреждение
> о несовпадении имени; «Всё равно перейти» (mTLS при этом работает). Лечится
> добавлением `IP:10.0.0.1` в SAN при следующей ротации серверного сертификата.

## 4. Выдача доступа КЛУБУ (полный сценарий)

Клуб = сервер FitIntel клуба (например nfs). Нужны: пир WireGuard + api_token клуба.

### Шаг 1. Создать/проверить клуб в платформе (если ещё нет)

```bash
CAC="--cacert nginx/certs/ca.crt"
CRT="--cert nginx/certs/client_<admin>.crt --key nginx/certs/client_<admin>.key"
curl $CAC $CRT -X POST https://127.0.0.1:8443/platform/clubs \
     -H 'Content-Type: application/json' -d '{"name":"Клуб <название>","slug":"<slug>"}'
# -> {"api_token": "club_...."}  ТОКЕН ПОКАЗЫВАЕТСЯ ОДИН РАЗ — записать.
```

### Шаг 2. Выдать клубу пир WireGuard

```bash
# на сервере платформы: увеличить PEERS на 1, docker compose up -d
# взять свободный конфиг:
docker compose exec wireguard ls /config | grep peer
docker compose exec wireguard cat /config/peer2/peer2.conf    # пример для peer2
```

### Шаг 3. На сервере клуба (требуется root/sudo)

```bash
# установить wireguard (Debian/Ubuntu):
sudo apt install -y wireguard
# положить полученный конфиг:
sudo cp peer2.conf /etc/wireguard/wg0.conf
sudo chmod 600 /etc/wireguard/wg0.conf
# поднять туннель и включить автозапуск:
sudo systemctl enable --now wg-quick@wg0
# проверка:
sudo wg show          # latest handshake — только что
ping -c3 10.0.0.1     # платформа отвечает
```

> На роутере клуба **ничего пробрасывать не нужно** — WG-клиент сам инициирует
> исходящие соединения (UDP 51820 наружу), NAT пробивается keepalive-пакетами.

### Шаг 4. Настроить heartbeat клуба на платформу (по туннелю)

Heartbeat клуба идёт напрямую в API платформы по адресу `10.0.0.1:8002` — **без**
mTLS-сертификата (авторизация — заголовком `X-Club-Token`):

```bash
# проверка с сервера клуба:
curl -s -X POST http://10.0.0.1:8002/platform/heartbeat \
     -H 'Content-Type: application/json' \
     -H 'X-Club-Token: club_<токен из шага 1>' \
     -d '{"version":"1.0","clients":82,"db_ok":true}'
# -> {"ok": true, "club": "<slug>", "server_time": ...}
```

Постоянная отправка heartbeat (cron каждые 5 минут):

```bash
sudo crontab -e
# строка:
*/5 * * * * curl -s -m 10 -X POST http://10.0.0.1:8002/platform/heartbeat -H 'Content-Type: application/json' -H 'X-Club-Token: club_<токен>' -d '{"version":"1.0"}' -o /dev/null
```

> Планово heartbeat будет слать агент клуба (ent_bridge v5 / отдельный агент) —
> задача в ROADMAP; до него достаточно cron-строки выше.

### Шаг 5. Проверка на платформе

```bash
# пир клуба виден:
docker compose exec wireguard wg show
# heartbeat дошёл:
curl $CAC $CRT https://127.0.0.1:8443/platform/clubs/<slug>/heartbeat
# в панели: клуб с заполненным last_seen
```

## 5. Примеры конфигураций (анатомия)

### 5.1 Пир клуба (то, что выдаём клубу) — `peer2.conf`

```ini
[Interface]
# IP пира в туннеле и приватный ключ пира (сгенерирован образом, уникален)
Address = 10.0.0.2/32
PrivateKey = <ПРИВАТНЫЙ_КЛЮЧ_ПИРА_dK3x...=

[Peer]
# Сервер платформы:
PublicKey = <ПУБЛИЧНЫЙ_КЛЮЧ_СЕРВЕРА_Xf9m...=
# Разрешить только служебную подсеть (интернет НЕ идёт в туннель)
AllowedIPs = 10.0.0.0/24
# Куда стучаться: белый статический IP платформы + порт WG
Endpoint = <ПУБЛИЧНЫЙ_IP>:51820
# Держит NAT/файрвол открытым, когда клиент за NAT (обязательно для клубов)
PersistentKeepalive = 25
```

### 5.2 Фрагмент серверного конфига (для понимания, в контейнере он свой)

```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <ПРИВАТНЫЙ_КЛЮЧ_СЕРВЕРА>

[Peer]  # peer2 = клуб «Демо»
PublicKey = <ПУБЛИЧНЫЙ_КЛЮЧ_ПИРА2>
AllowedIPs = 10.0.0.2/32
```

### 5.3 Соответствие пиров клубам (ведём таблицу!)

| Пир | IP | Клуб | Кому выдан | Дата |
|---|---|---|---|---|
| peer1 | 10.0.0.2 | demo | — | — |
| peer2 | 10.0.0.3 | <клуб> | <контакт> | 22.10.2026 |
| peer11 | 10.0.0.11 | — | админ andrei@fixintel.ru | 22.10.2026 |

Хранить в `deploy/platform/WG_PEERS.md` (не секретно: публичные ключи и IP,
приватных ключей в таблице нет).

## 6. Отзыв доступа (расторжение с клубом / утеря конфига)

```bash
# 1) на сервере платформы: удалить пира (пересоздать wg с новым конфигом peer'а
#    проще всего выпустить НОВЫЙ пир и отдать его, а старый забыть)
# 2) на платформе: перевыпустить токен клуба (старый сгорает):
curl $CAC $CRT -X POST https://127.0.0.1:8443/platform/clubs/<slug>/token
# 3) на сервере клуба при расторжении:
sudo systemctl disable --now wg-quick@wg0
sudo rm /etc/wireguard/wg0.conf
# 4) таблицу WG_PEERS.md обновить
```

> Полноценный «отзыв пира» (kill по публичному ключу) в linuxserver/wireguard
> делается правкой конфигов в volume; проще перевыпуск пира + ротация токена.

## 7. Диагностика

| Симптом | Причина | Решение |
|---|---|---|
| `wg show`: handshake 0, transfer 0 | UDP 51820 не проброшен / закрыт провайдером; неверный Endpoint | проверить проброс роутера; `docker compose logs wireguard` |
| handshake есть, пинг 10.0.0.1 нет | AllowedIPs пира не содержит 10.0.0.0/24 | исправить conf, `sudo systemctl restart wg-quick@wg0` |
| работало, перестало | сменился белый IP (не статика!) или NAT закрылся | убедиться что IP статический; keepalive=25 у клиента |
| heartbeat 401 «unknown club token» | токен неверный/ротирован | запросить актуальный у платформы (шаг 1) |
| heartbeat 400 снаружи без WG | mTLS требует сертификат от всех | heartbeat только по туннелю `10.0.0.1:8002` |
| на платформе «нет handshake» у пира | клуб выключен / wg не в автозапуске | на клубе: `systemctl enable --now wg-quick@wg0` |

## 8. Чек-лист подключения нового клуба

- [ ] клуб создан в платформе, api_token сохранён (показывается один раз!)
- [ ] пир выдан (PEERS+1, conf получен клубом), запись в WG_PEERS.md
- [ ] на сервере клуба: wireguard установлен, wg0.conf (600), автозапуск
- [ ] `ping 10.0.0.1` с сервера клуба — ок
- [ ] heartbeat руками — `{"ok": true}`; cron-строка добавлена
- [ ] на платформе: `wg show` — handshake, `/platform/clubs/<slug>/heartbeat` — данные
- [ ] лицензия клуба выпущена и активирована (PLATFORM_DEPLOY_GUIDE.md §5)

---
## Дополнение от 22.10 (после боевой установки)
- **Отзыв сертификата**: вместо openssl ca -revoke (падает с Error creating serial number index на сертификатах, выпущенных через openssl x509) писать в index.txt напрямую строку со статусом R: printf \"R\\t<expiry>\\t<дата_отзыва_yyMMddHHmmssZ>\\t<serial>\\tunknown\\t/CN=<email>\" >> index.txt, затем openssl ca -gencrl и restart nginx. В index.txt не должно быть дублей серийника.
- **Порт WireGuard платформы**: если на сервере уже есть WG (наш кейс: контейнер wireguard-hub на 51820), платформе назначаем другой внешний порт (51829): sed замены в docker-compose.yml (порт публикации + SERVERPORT) + проброс UDP 51829 на роутере. Все peer-конфиги платформы автоматически получат Endpoint <IP>:51829.
