#!/usr/bin/env bash
# FitIntel Pro — ежедневный бэкап БД (cron: 0 3 * * *)
set -euo pipefail

ENV_FILE="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup.env}"
if [ -f "$ENV_FILE" ]; then
  set -a; source "$ENV_FILE"; set +a
fi

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/fitintel-pro/deploy}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.test.yml}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-fitnexus_user}"
DB_NAME="${DB_NAME:-fitnexus_ai}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
LOCAL_DIR="${LOCAL_DIR:-$HOME/fitintel-backups}"
STAMP="$(date +%F_%H%M)"
FILE="db_$STAMP.sql.gz"

mkdir -p "$LOCAL_DIR"
echo "[$(date '+%F %T')] === Бэкап $DB_NAME ==="
docker compose -f "$COMPOSE_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$LOCAL_DIR/$FILE"
echo "[$(date '+%T')] Локально: $LOCAL_DIR/$FILE ($(du -h "$LOCAL_DIR/$FILE" | cut -f1))"

if [ "${HDD_ENABLE:-0}" = "1" ]; then
  if [ -d "${HDD_MOUNT:-/mnt/hdd}" ] && mountpoint -q "${HDD_MOUNT:-/mnt/hdd}"; then
    mkdir -p "$HDD_MOUNT/fitintel-backups"
    cp "$LOCAL_DIR/$FILE" "$HDD_MOUNT/fitintel-backups/"
    echo "[$(date '+%T')] HDD: скопировано -> $HDD_MOUNT/fitintel-backups/"
  else
    echo "[$(date '+%T')] HDD: ПРОПУСК — $HDD_MOUNT не смонтирован!"
  fi
fi

if [ "${CLOUD_ENABLE:-0}" = "1" ]; then
  if command -v rclone >/dev/null 2>&1; then
    rclone copy "$LOCAL_DIR/$FILE" "${RCLONE_REMOTE:-yandex}:fitintel-backups/" \
      && echo "[$(date '+%T')] Облако: загружено -> ${RCLONE_REMOTE:-yandex}:fitintel-backups/"
  else
    echo "[$(date '+%T')] Облако: ПРОПУСК — rclone не установлен!"
  fi
fi

find "$LOCAL_DIR" -name "db_*.sql.gz" -mtime "+$RETENTION_DAYS" -delete
echo "[$(date '+%T')] Ротация: храним $RETENTION_DAYS дней"
echo "[$(date '+%T')] === Готово ==="
