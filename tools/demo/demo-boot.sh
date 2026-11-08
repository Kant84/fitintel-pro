#!/usr/bin/env bash
# demo-boot.sh — обязательное обновление демо-статистики при загрузке VM.
# Вызывается systemd-сервисом demo-fill.service (enable при установке стенда).
cd /home/andrei/fitintel-demo || exit 1
echo "$(date -Is) boot-fill start" >> /var/log/demo-fill.log
# ждём подъёма стенда (контейнеры стартуют сами по restart-policy)
for i in $(seq 1 40); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/v1/health/ 2>/dev/null || echo 000)
  [ "$CODE" = "200" ] && break
  sleep 10
done
docker cp tools/demo/demo_stats_fill.py deploy-api-1:/tmp/fill.py
docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec -T api \
  env PYTHONPATH=/app python /tmp/fill.py --days 7 --per-day 140 >> /var/log/demo-fill.log 2>&1
echo "$(date -Is) boot-fill done (health=$CODE)" >> /var/log/demo-fill.log
