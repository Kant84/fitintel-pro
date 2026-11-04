#!/bin/bash
# Медиа/документы/фото/брендинг -> $OUT/media_<volume>_<ts>.tar.gz (ротация 14).
# Переопределить каталог: BACKUP_OUT=/path ... или кроном.
set -e
BASE="$(cd "$(dirname "$0")/../../" && pwd)"
OUT="${BACKUP_OUT:-$BASE/deploy/backups}"
TS=$(date +%Y%m%d_%H%M%S)
IMG=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep '^postgres' | head -1)
mkdir -p "$OUT"
for V in $(docker volume ls --format '{{.Name}}' | grep -iE 'media|document|brand|face_photo|clients_data|static_products|static_scan|static_trainers'); do
  docker run --rm -v "$V":/data:ro -v "$OUT":/out "$IMG" \
    tar czf "/out/media_${V}_${TS}.tar.gz" -C /data . 2>/dev/null && echo "media OK: $V" || echo "media SKIP: $V"
done
cd "$OUT"
ls -t media_*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
echo "MEDIA_BACKUP_OK=$TS"
