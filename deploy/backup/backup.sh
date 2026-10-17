#!/bin/bash
# FitIntel Pro: ночной бэкап БД (запускать вечером, пока ПК не спит)
set -e
BACKUP_DIR=/home/andrei/fitintel-pro/deploy/backups
TS=$(date +%Y%m%d_%H%M%S)
OUT=$BACKUP_DIR/fitintel_${TS}.sql.gz
docker exec deploy-db-1 sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$OUT"
find $BACKUP_DIR -name "fitintel_*.sql.gz" -mtime +14 -delete
echo "$(date '+%F %T') backup OK: $OUT ($(du -h "$OUT" | cut -f1))"