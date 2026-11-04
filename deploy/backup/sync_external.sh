#!/bin/bash
# Внешняя копия свежих бэкапов на другой хост (E4).
# Обязательные env: SYNC_USER, SYNC_HOST, SYNC_DEST. SSH_KEY по умолчанию /root/.ssh/backup_key.
set -e
: "${SYNC_USER:?set SYNC_USER}"; : "${SYNC_HOST:?set SYNC_HOST}"; : "${SYNC_DEST:?set SYNC_DEST}"
BASE="$(cd "$(dirname "$0")/../../" && pwd)"
OUT="$BASE/deploy/backups"
KEY="${SSH_KEY:-/root/.ssh/backup_key}"
OPTS="-i $KEY -o StrictHostKeyChecking=accept-new"
ssh $OPTS "$SYNC_USER@$SYNC_HOST" "mkdir -p $SYNC_DEST"
LATEST=$(ls -t "$OUT"/fitintel_full_*.tar.gz 2>/dev/null | head -1)
[ -n "$LATEST" ] && scp $OPTS "$LATEST" "$SYNC_USER@$SYNC_HOST:$SYNC_DEST/"
MEDIA=$(ls -t "$OUT"/media_*_*.tar.gz 2>/dev/null | head -8)
[ -n "$MEDIA" ] && scp $OPTS $MEDIA "$SYNC_USER@$SYNC_HOST:$SYNC_DEST/" || true
echo "sync OK: $(basename "$LATEST")"
