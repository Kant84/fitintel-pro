# FitIntel Platform — канал удалённого доступа (mTLS + WireGuard)

**Документация для администраторов и службы поддержки FitIntel Pro.**
Описывает, как устроен защищённый канал доступа к платформе, как его развернуть с нуля
и как выдать доступ новому сотруднику.

---

## 1. Что это и зачем

Платформа (веб-панель платформенного администратора) управляет клубами франшизы:
лицензиями, доступом поддержки к клубам, телеметрией. Доступ к ней из интернета
открыт только через **взаимную TLS-аутентификацию (mTLS)**:

- сервер предъявляет сертификат клиенту (как в обычном HTTPS);
- **клиент обязан предъявить сертификат серверу** — без него соединение разрывается
ещё на этапе TLS-рукопожатия.

Это заменяет логин/пароль на канале: доступ есть только у того, у кого на устройстве
установлен действующий клиентский сертификат, выпущенный нашим CA. Утёкший пароль
ничего не даёт; украденный ноутбук без сертификата — тоже.

Клубы подключаются к платформе не через интернет, а по **WireGuard** (VPN-туннель
«клуб → платформа»). Туннель шифрует служебный трафик (heartbeat, телеметрия) и не
требует открывать порты клуба наружу.

## 2. Архитектура

```javascript
  Администратор/поддержка                Клуб (FitIntel сервер)
  ┌──────────────────┐                  ┌──────────────────────┐
  │ ноутбук/телефон  │                  │ ent_bridge / агент   │
  │ + client cert    │                  │ (wireguard peer)     │
  └────────┬─────────┘                  └──────────┬───────────┘
           │ HTTPS + mTLS, TCP 8443                │ WireGuard UDP 51820
           │                                       │
           ▼                                       ▼
  ┌───────────────────────────────────────────────────────┐
  │              Сервер платформы (домашний/VPS)           │
  │  ┌───────────┐   ┌──────────────┐   ┌───────────────┐  │
  │  │   nginx   │──▶│ platform_api │──▶│  platform_db  │  │
  │  │ mTLS:8443 │   │  (этап Б)    │   │  PostgreSQL   │  │
  │  └───────────┘   └──────────────┘   └───────────────┘  │
  │  ┌───────────┐                                        │
  │  │ wireguard │  ← принимает туннели клубов             │
  │  └───────────┘                                        │
  └───────────────────────────────────────────────────────┘
           ▲
           │ TCP 8080 → редирект на 8443
```

**Компоненты (docker-compose на сервере платформы):**

| Сервис | Образ | Назначение | Порты |
| --- | --- | --- | --- |
| `nginx` | nginx:alpine | Терминация mTLS, редирект 8080→8443, проксирование в platform_api | `8080`, `8443` |
| `platform_db` | postgres:16-alpine | База платформы (клубы, админы, аудит, история лицензий) | только `127.0.0.1:5433` |
| `wireguard` | linuxserver/wireguard | VPN-сервер для клубов | `51820/udp` |
| `platform_api` | (этап Б) | FastAPI приложения | внутренний, за nginx |

**Проброс портов на роутере (внешний → сервер платформы):**

| Внешний порт | Протокол | Куда | Для чего |
| --- | --- | --- | --- |
| `<ПУБЛИЧНЫЙ_IP>:8443` | TCP | `<СЕРВЕР_ПЛАТФОРМЫ>:8443` | панель, mTLS |
| `<ПУБЛИЧНЫЙ_IP>:51820` | UDP | `<СЕРВЕР_ПЛАТФОРМЫ>:51820` | WireGuard клубов |

> ⚠️ Внешний порт 8443 должен принадлежать **только одному** правилу. Если на роутере
> есть старые/мёртвые правила на тот же порт (например, MeshCentral) — удалите их,
> иначе какая-то из служб снаружи не будет отвечать.

**Файловая структура (в репозитории, deploy/platform/):**

```javascript
deploy/platform/
├── docker-compose.yml        # сервисы выше
├── .env                      # НЕ в git: PUBLIC_IP, PLATFORM_DB_PASSWORD
├── .env.example              # шаблон
├── nginx/
│   ├── nginx.conf            # events/http + server-блоки 8080/8443
│   └── certs/                # НЕ в git (*.key, *.p12, ca.key игнорируются)
│       ├── ca.crt / ca.key   # корневой CA (ключ — 600!)
│       ├── ca.crl            # список отзыва (должен быть валидным PEM!)
│       ├── ca.cnf, index.txt, serial, crlnumber, ca.srl  # инфраструктура CA
│       ├── server.crt / server.key   # серверный сертификат
│       └── client_<email>.{crt,key,p12}  # сертификаты администраторов
├── scripts/gen_certs.sh      # генерация CA + серверного + клиентских сертификатов
└── secrets/                  # Docker secrets (LICENSE_PRIVATE_KEY_PATH и т.п.)
```

## 3. Сертификаты: кто есть кто

| Сертификат | CN | Срок | Кому выдаётся | Куда ставится |
| --- | --- | --- | --- | --- |
| **CA** (самоподписанный) | `FitIntel Platform CA` | 10 лет | никому — корень доверия | сервер (nginx) + в устройства админов (внутри .p12) |
| **Серверный** | `fitintel-platform` | 825 дней | только серверу | nginx |
| **Клиентский** | email админа, напр. `admin@fitintel.local` | 825 дней | **один на человека** (не на клуб!) | устройство админа (.p12 → браузер/ОС) |

Цепочка доверия: клиентский сертификат подписан CA → nginx принимает любой сертификат,
подписанный `ca.crt`, **не находящийся в ca.crl**.

## 4. Развёртывание канала с нуля (на сервере платформы)

Предполагается: Linux + Docker + docker compose, репозиторий склонирован.

```bash
cd <репозиторий>/deploy/platform

# 1) Конфигурация
cp .env.example .env
# отредактируйте .env: PUBLIC_IP=<ПУБЛИЧНЫЙ_IP>,
# PLATFORM_DB_PASSWORD=<случайный, мин. 24 символа>
# (генерация: python3 -c 'import secrets;print(secrets.token_urlsafe(24))')

# 2) Сертификаты (CA + серверный + первый клиентский)
mkdir -p nginx/certs          # важно: каталог должен принадлежать пользователю!
bash scripts/gen_certs.sh admin@fitintel.local
# на запрос "Enter Export Password" для .p12: Enter дважды (без пароля)
# или задайте пароль — он запрашивается при импорте сертификата в устройство

# 3) Валидный CRL (пустой файл nginx не примет!)
cd nginx/certs
cat > ca.cnf <<'EOF'
[ca]
default_ca = CA_def
[CA_def]
database = ./index.txt
serial = ./serial
crlnumber = ./crlnumber
default_md = sha256
default_crl_days = 30
certificate = ./ca.crt
private_key = ./ca.key
EOF
touch index.txt
echo 1000 > serial
echo 1000 > crlnumber
openssl ca -gencrl -config ca.cnf -out ca.crl

# 4) Запуск
cd ../..
docker compose up -d
docker compose ps        # все контейнеры Up (nginx без Restarting)

# 5) Проверка (см. раздел 6)
curl -k https://127.0.0.1:8443/health
```

## 5. Выдача доступа новому администратору

Один сертификат — на человека, на все его устройства выдаётся копия того же .p12.
Порядок: администратор платформы генерирует сертификат на сервере и **передаёт .p12
только по защищённому каналу** (лично, мессенджер с E2E; НЕ email).

**На сервере платформы:**

```bash
cd <репозиторий>/deploy/platform/nginx/certs
EMAIL="ivanov@fitintel.local"

# ключ + запрос + подписание CA
openssl genrsa -out "client_${EMAIL}.key" 2048
openssl req -new -key "client_${EMAIL}.key" -out client.csr -subj "/CN=${EMAIL}"
printf "extendedKeyUsage=clientAuth\n" > ext.cnf
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out "client_${EMAIL}.crt" -days 825 -sha256 -extfile ext.cnf
rm -f client.csr ext.cnf

# пакет для установки на устройство (сертификат + ключ + CA)
openssl pkcs12 -export -out "client_${EMAIL}.p12" \
  -inkey "client_${EMAIL}.key" -in "client_${EMAIL}.crt" -certfile ca.crt
# Enter дважды — без пароля, или задайте пароль и сообщите его админу отдельно

ls -l "client_${EMAIL}.p12"
# забрать файл с сервера (scp/rsync) и передать админу; на сервере хранить можно —
# каталог certs не в git, но ограничьте доступ: chmod 600 client_*.p12
```

**Перенос файла на ПК админа (пример с Windows):**

```powershell
scp andrei@<СЕРВЕР_ПЛАТФОРМЫ>:~/fitintel-pro/deploy/platform/nginx/certs/client_ivanov@fitintel.local.p12 $env:USERPROFILE\Downloads\
```

**Установка на устройство админа:**

| Платформа | Как установить |
| --- | --- |
| **Windows** | Двойной клик по .p12 → «Локальный компьютер» → хранилище «Личное». CA ставится туда же (включается галкой в мастере). |
| **Chrome/Edge (Windows)** | Сертификат ставится в ОС (см. выше) — браузер его подхватывает автоматически. |
| **Firefox** | Настройки → Приватность → Сертификаты → «Просмотр сертификатов» → Импорт → .p12. Firefox использует своё хранилище, в ОС ставить не нужно. |
| **Android** | Настройки → Безопасность → Установить сертификат → «Сертификат ПК» → .p12. |
| **iOS** | Отправить .p12 в Files → открыть → «Установить профиль», затем включить доверие к CA: Настройки → Основные → Об этом устройстве → Доверие сертификатам. |

## 6. Проверка доступа

**Позитивный тест (с клиентским сертификатом) — с любой машины админа:**

```bash
curl --cert client_<email>.crt --key client_<email>.key \
     https://<ПУБЛИЧНЫЙ_IP>:8443/health
# ожидается: {"ok": true}
```

**Негативный тест (без сертификата) — доступ обязан быть закрыт:**

```bash
curl -k https://<ПУБЛИЧНЫЙ_IP>:8443/health
# ожидается: 400 No required SSL certificate was sent
#            (обрыв TLS-рукопожатия на стороне сервера)
```

**Проверка с браузера:** открыть `https://<ПУБЛИЧНЫЙ_IP>:8443/` — без сертификата
браузер покажет ошибку `400 No required SSL certificate was sent`; с импортированным
.p12 — страница открывается без вопросов.

**Регламент:** после выдачи сертификата и после каждого изменения конфигурации
выполняйте оба теста. Только позитив без негатива = mTLS не работает.

## 7. Эксплуатация

### 7.1 Отзыв сертификата (утеря устройства, увольнение)

```bash
cd <репозиторий>/deploy/platform/nginx/certs

# 1) сертификат должен быть в базе CA — при создании через openssl x509
#    (как у нас) записи в index.txt нет, поэтому:
SERIAL=$(openssl x509 -in client_<email>.crt -noout -serial | cut -d= -f2)
printf "V\t260101000000Z\t\t%s\tunknown\t/CN=<email>\n" "$SERIAL" >> index.txt

# 2) отозвать и пересоздать CRL
openssl ca -revoke client_<email>.crt -config ca.cnf
openssl ca -gencrl -config ca.cnf -out ca.crl

# 3) nginx читает CRL на старте — обязателен reload
cd ../.. && docker compose restart nginx
```

> ⚠️ Отзыв вступает в силу только после `restart nginx`. Если отозванный сертификат
> продолжает работать — вы забыли перезапустить nginx.

### 7.2 Продление (ротация)

| Что | Срок | Когда и как продлевать |
| --- | --- | --- |
| CA | 10 лет | за год до конца: создать новый CA, перевыпустить все сертификаты, разослать .p12 заново |
| Серверный / клиентские | 825 дней (~2 года 3 мес) | по факту уведомления в разделе 8 (ошибка `certificate has expired`) |
| CRL | 30 дней (поле nextUpdate) | даже если отзывов не было: `openssl ca -gencrl -config ca.cnf -out ca.crl` + `docker compose restart nginx` — рекомендуется раз в месяц (записать в cron сервера) |

Автоматической ротации сейчас нет (задача в ROADMAP) — контроль сроков ведём вручную,
вывод дат:

```bash
cd nginx/certs
for f in server.crt client_*.crt; do echo -n "$f: "; openssl x509 -in "$f" -noout -enddate; done
```

### 7.3 Диагностика типовых ошибок

| Симптом | Причина | Решение |
| --- | --- | --- |
| `400 No required SSL certificate was sent` | у клиента не установлен/не выбран сертификат | импортировать .p12 (раздел 5), в Firefox выбрать сертификат при запросе |
| `tlsv13 alert certificate expired` | сертификат истёк | перевыпустить (раздел 5), выдать новый .p12 |
| `unknown ca` / `self signed certificate in certificate chain` | браузер не доверяет CA | импортировать ca.crt (внутри .p12 он уже есть); iOS — включить доверие вручную |
| `certificate revoked` | сертификат в CRL | выдать новый сертификат |
| `Connection refused` по внешнему IP, локально работает | роутер: нет/не тот проброс 8443; конфликт правил на один порт | проверить таблицу проброса; убедиться, что порт 8443 занят только платформой |
| `Connection refused` и локально | nginx упал/не поднят | `docker compose ps`, `docker compose logs nginx` |
| `cannot load CRL ... PEM_read_bio_X509_CRL() failed` | ca.crl пустой/битый | создать валидный CRL (раздел 4, шаг 3) и `docker compose restart nginx` |
| curl: `could not load PEM client certificate` | неверный путь к .crt/.key или CRLF-переносы в ключе | проверить пути; ключ должен быть в PEM (начинается с `-----BEGIN`) |

### 7.4 Команды наблюдения

```bash
cd <репозиторий>/deploy/platform
docker compose ps                     # состояние всех сервисов
docker compose logs nginx --tail=30   # ошибки mTLS, 400-е, адреса клиентов
docker compose logs wireguard         # подключения/отключения клубов
# кто подключён по WireGuard прямо сейчас:
docker compose exec wireguard wg show
```

## 8. Файрвол хоста (применить сразу после развёртывания)

По умолчанию на сервере платформы открыт **весь** входящий трафик. Закрываем всё,
кроме трёх служб. **Критический нюанс:** опубликованные Docker-порты (8443, 8080, 51820)
обходят обычную цепочку `INPUT` и контролируются цепочкой `DOCKER-USER` — поэтому
просто `ufw` здесь недостаточно, правила даём через `iptables`.

```bash
# 0) Узнайте имя внешнего интерфейса (обычно eth0/enp*s0) и ПОДСТАВЬТЕ вместо eth0
ip route | grep default

sudo apt install -y iptables-persistent   # автосохранение правил при перезагрузке

# 1) SSH: разрешить только с IP администраторов, остальным — закрыть
sudo iptables -A INPUT -p tcp --dport 22 -s <IP_АДМИНА_1> -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -s <IP_АДМИНА_2> -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j DROP

# 2) Службы платформы (через DOCKER-USER — именно так проходит Docker-трафик)
sudo iptables -A DOCKER-USER -i eth0 -p tcp --dport 8443 -j ACCEPT   # mTLS панель
sudo iptables -A DOCKER-USER -i eth0 -p udp --dport 51820 -j ACCEPT  # WireGuard клубов
sudo iptables -A DOCKER-USER -i eth0 -p tcp --dport 8080 -j ACCEPT   # редиректор (можно удалить строку, если 8080 не нужен снаружи)
sudo iptables -A DOCKER-USER -i eth0 -j DROP                         # всё остальное в Docker снаружи — запретить
sudo iptables -A DOCKER-USER -j RETURN                               # локальный и служебный трафик — как было

# 3) Утилиты наблюдения и сохранение
sudo iptables -L INPUT -n -v --line-numbers
sudo iptables -L DOCKER-USER -n -v --line-numbers
sudo netfilter-persistent save
```

> ⚠️ **Порядок безопасного применения:** выполняйте из консоли, к которой есть
> запасной доступ (IPMI/вторая сессия/физический доступ). После шага 1 сначала
> **откройте новую SSH-сессию и убедитесь, что она устанавливается**, и только потом
> продолжайте. Ошибка в шаге 1 отрежет вас от сервера.

Проверка после применения: из домашней сети `curl -k https://<ПУБЛИЧНЫЙ_IP>:8443/health`
(400 — файрвол пропустил, nginx требует сертификат), а с любого чужого порта, например
`curl telnet://<ПУБЛИЧНЫЙ_IP>:5433` — обрыв по таймауту (доступ закрыт).

## 9. Fail2ban (защита от сканирования и брутфорса SSH)

Для mTLS сертификат обязателен, поэтому взлом канала через подбор невозможен — но
сервер всё равно «светится» сканерам (тысячи 400-х в логах) и SSH перебирают боты.
Fail2ban банит IP, которые слишком часто получают отказ.

**Шаг 1. Логи nginx — в каталог на хосте** (fail2ban в контейнере не видит логи
docker'а). В `docker-compose.yml` у сервиса `nginx` добавьте volume и перезапустите:

```yaml
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - ./logs:/var/log/nginx          # <-- добавить
```

а в `nginx/nginx.conf` в блок `http {` — явные пути логов:

```nginx
    access_log /var/log/nginx/platform_access.log;
    error_log  /var/log/nginx/platform_error.log;
```

```bash
mkdir -p logs && docker compose up -d && docker compose restart nginx
```

**Шаг 2. Установка и фильтр:**

```bash
sudo apt install -y fail2ban

sudo tee /etc/fail2ban/filter.d/fitintel-mtls.conf > /dev/null <<'EOF'
# Баним IP, которые ломятся без клиентского сертификата (400 от nginx)
[Definition]
failregex = ^<HOST> -.*"(GET|POST|HEAD|PUT|DELETE).*HTTP/[0-9.]+" 400
ignoreregex =
EOF

sudo tee /etc/fail2ban/jail.d/fitintel.conf > /dev/null <<'EOF'
[DEFAULT]
bantime  = 86400        # бан на сутки
findtime = 600          # окно подсчёта: 10 минут
maxretry = 5            # 5 отказов за окно -> бан
# не банить: локалхост и служебную подсеть WireGuard
ignoreip = 127.0.0.1/8 10.0.0.0/24

[sshd]
enabled = true          # стандартная защита SSH (пары логин/пароль перебирают все)

[fitintel-mtls]
enabled  = true
filter   = fitintel-mtls
logpath  = /home/andrei/fitintel-pro/deploy/platform/logs/platform_access.log
maxretry = 10           # сканеры ломятся сотнями — 10 попыток для спокойных клиентов
EOF

sudo systemctl restart fail2ban
sudo fail2ban-client status                # оба jail: sshd + fitintel-mtls
sudo fail2ban-client status fitintel-mtls  # текущие баны
```

**Шаг 3. Проверка фильтра на реальном логе** (до появления банов — на сырых данных):

```bash
# сгенерируйте несколько 400-х и проверьте, что fail2ban их «видит»:
curl -k https://<ПУБЛИЧНЫЙ_IP>:8443/health   # несколько раз с другой машины
sudo fail2ban-regex /home/andrei/fitintel-pro/deploy/platform/logs/platform_access.log fitintel-mtls
# в выводе: "N matched" — фильтр работает
```

> ⚠️ Не баньте сами себя: `ignoreip` обязан содержать `10.0.0.0/24` (WireGuard
> клубов и ваших же админов, если они ходят по WG) и ваши постоянные IP.

## 10. Чек-лист нового сервера / нового клуба

**Новый сервер платформы:**

- [ ] Docker + compose установлены, репозиторий склонирован
- [ ] `.env` заполнен (PUBLIC_IP, PLATFORM_DB_PASSWORD)
- [ ] `bash scripts/gen_certs.sh <email владельца>` → сертификаты созданы
- [ ] Валидный `ca.crl` создан (раздел 4, шаг 3)
- [ ] `docker compose up -d` → все сервисы `Up`
- [ ] Позитивный и негативный тест (раздел 6) — **оба**
- [ ] Проброс роутера: TCP 8443 + UDP 51820 → серверу, конфликтов портов нет
- [ ] Файрвол применён (раздел 8), вторая SSH-сессия проверена, `netfilter-persistent save` выполнен
- [ ] Fail2ban: оба jail активны, `fail2ban-regex` показывает совпадения (раздел 9)
- [ ] Внешний тест с клиентским сертификатом через `<ПУБЛИЧНЫЙ_IP>` — `{"ok": true}`

**Новый администратор:**

- [ ] Сертификат сгенерирован (раздел 5), .p12 передан по защищённому каналу
- [ ] Установлен на устройстве, п.6 пройден
- [ ] Ответственный записал: email ↔ дата выдачи ↔ срок (контроль ротации)

**Новый клуб (после этапа Б платформы):**

- [ ] В `wireguard_config/peerN/` выдан `peerN.conf` клубу
- [ ] Клуб: `wg-quick up peerN.conf` (PersistentKeepalive уже в конфиге)
- [ ] Клуб добавлен в `platform_db` (таблица `clubs`)
- [ ] `docker compose exec wireguard wg show` — peer виден, handshake есть

## 11. Ограничения текущей реализации (в ROADMAP)

- Нет автоматической ротации сертификатов и авто-CRL по cron — вручную (раздел 7.2);
- Нет отдельного файрвола на хосте (iptables policy ACCEPT) — рекомендуется закрыть
всё кроме 22/8443/51820/8080;
- Доменное имя (например, `admin.fitintel.ru`) не подключено — сертификат сервера
привязан к IP; при появлении домена добавить его в SAN серверного сертификата;
- fail2ban не настроен — для mTLS менее критично (нужен сертификат), но защита от
сканирования портов полезна.

---

*Версия документа: 1.0 (22.10.2026). Правки — только через репозиторий (Windows → commit → push).*