#!/usr/bin/env bash
# demo-install.sh v2 — полный подъём демо-стенда FitIntel Pro из пакета (12 шагов).
# Запуск: sudo ./demo-install.sh  (файлы пакета рядом со скриптом).
# Идемпотентно; в конце — автообновление статистики при каждой загрузке VM.
set -euo pipefail
cd "$(dirname "$0")"
PACK_DIR="$(pwd)"
DC="docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml"

step() { echo; echo "== $1 =="; }

step "1/12 Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh || { apt-get update && apt-get install -y docker.io docker-compose-v2; }
fi
docker compose version >/dev/null 2>&1 || { apt-get update && apt-get install -y docker-compose-v2; }
docker info >/dev/null
echo "DOCKER_OK"

step "2/12 Исходники (fitintel-demo)"
if [ ! -d fitintel-demo ]; then
  if [ -f fitintel-pro-src.tar.gz ]; then
    mkdir fitintel-demo && tar xzf fitintel-pro-src.tar.gz -C fitintel-demo --strip-components=1
  else
    git clone https://github.com/Kant84/fitintel-pro.git fitintel-demo
  fi
fi
[ -f fitintel-demo/deploy/docker-compose.prod.yml ] || { echo "Исходники не найдены"; exit 1; }
cd fitintel-demo
echo "SRC_OK"

step "3/12 Внешние volumes"
for v in deploy_static_trainers deploy_static_products deploy_static_scan deploy_clients_data deploy_media_data deploy_accounting_data; do
  docker volume create "$v" >/dev/null
done
echo "VOLUMES_OK=$(docker volume ls -q | grep -c '^deploy_')"

step "4/12 Секреты и .env"
mkdir -p /etc/fitintel/secrets
cp "$PACK_DIR/media_master_key" /etc/fitintel/secrets/media_master_key
chmod 600 /etc/fitintel/secrets/media_master_key
cp "$PACK_DIR/env-clone.txt" deploy/.env
chmod 600 deploy/.env
echo "SECRETS_OK"

step "5/12 Docker-образ fitintel:prod"
if ! docker image inspect fitintel:prod >/dev/null 2>&1; then
  gunzip -c "$PACK_DIR"/fitintel-prod-*.tar.gz | docker load
fi
docker images --format '{{.Repository}}:{{.Tag}}' | grep -x 'fitintel:prod'
echo "IMAGE_OK"

step "6/12 База данных"
$DC up -d db
sleep 15
CID=$($DC ps -q db)
DMP=$(ls -t "$PACK_DIR"/fitintel-db-*.dump | head -1)
docker cp "$DMP" "$CID":/tmp/restore.dump
DB_USER=$(grep '^POSTGRES_USER=' deploy/.env | cut -d= -f2-)
DB_NAME=$(grep '^POSTGRES_DB='   deploy/.env | cut -d= -f2-)
docker exec "$CID" pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists /tmp/restore.dump
docker exec "$CID" psql -U "$DB_USER" -d "$DB_NAME" -c "UPDATE users SET failed_login_count=0, locked_until=NULL;"
CLIENTS=$(docker exec "$CID" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM clients;")
echo "DB_OK clients=$CLIENTS"

step "7/12 Полный старт"
$DC up -d
CODE=000
for i in 1 2 3; do
  sleep 30
  CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/v1/health/ 2>/dev/null || echo 000)
  echo "health attempt $i: $CODE"
  [ "$CODE" = "200" ] && break
done

step "8/12 Медиа (опционально)"
MED=$(ls -t "$PACK_DIR"/media-*.tar.gz 2>/dev/null | head -1 || true)
if [ -n "${MED}" ]; then
  docker run --rm -v deploy_media_data:/data -v "$PACK_DIR":/src alpine tar xzf "/src/$(basename "$MED")" -C /data 2>/dev/null && echo MEDIA_OK || echo MEDIA_SKIP
fi

step "9/12 mDNS (fitintel.local)"
apt-get install -y avahi-daemon >/dev/null 2>&1 || true
systemctl enable --now avahi-daemon 2>/dev/null || true

step "10/12 LT-клиенты (фейковые, для статистики и потока)"
docker cp tools/loadtest/generate_data.py deploy-api-1:/tmp/gen.py
$DC exec -T api env PYTHONPATH=/app python /tmp/gen.py --clients 3000

step "11/12 Статистика за 60 дней (визиты + платежи, даты от сегодня)"
docker cp tools/demo/demo_stats_fill.py deploy-api-1:/tmp/fill.py
$DC exec -T api env PYTHONPATH=/app python /tmp/fill.py --days 60 --per-day 140

step "12/12 Автообновление статистики при загрузке VM"
cat > /etc/systemd/system/demo-fill.service <<'UNIT'
[Unit]
Description=FitIntel demo: stats fill on boot
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/home/andrei/fitintel-demo/tools/demo/demo-boot.sh
TimeoutStartSec=900
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable demo-fill.service

echo
echo "================ ИТОГ ================"
echo "HEALTH=$CODE (ожидание 200)"
echo "CLIENTS=$CLIENTS"
echo "Десктоп:  http://fitintel.local  (логин/пароль админа — ваши с боевого стенда)"
echo "Живой поток во время демо: cd fitintel-demo && docker cp tools/demo/demo_flow.py deploy-api-1:/tmp/flow.py && $DC exec -T api env PYTHONPATH=/app python /tmp/flow.py --target 25 --interval 15"
