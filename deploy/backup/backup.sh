#!/usr/bin/env bash
# FitIntel Pro: полный бэкап production БД, файлов, лицензии и настроек клуба.
set -euo pipefail
umask 077

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$BASE/deploy/backups}"
COMPOSE_FILE="${FITINTEL_COMPOSE_FILE:-$BASE/deploy/docker-compose.prod.yml}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
ACCOUNTING_DB="/app/data_accounting/fitintel_accounting.db"
ACCOUNTING_TMP="/tmp/fitintel_accounting_backup.db"
SECRETS_DIR="${FITINTEL_SECRETS_DIR:-/etc/fitintel/secrets}"

for COMMAND in docker tar gzip find; do
    if ! command -v "$COMMAND" >/dev/null 2>&1; then
        echo "$(date '+%F %T') backup ERROR: команда $COMMAND не найдена" >&2
        exit 1
    fi
done
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "$(date '+%F %T') backup ERROR: не найден $COMPOSE_FILE" >&2
    exit 1
fi
if [ ! -f "$BASE/deploy/.env" ]; then
    echo "$(date '+%F %T') backup ERROR: не найден deploy/.env" >&2
    exit 1
fi
if [ ! -d "$SECRETS_DIR" ]; then
    echo "$(date '+%F %T') backup ERROR: не найден $SECRETS_DIR" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/fitintel_full_${TS}.tar.gz"
TMP_OUT="$OUT.tmp"
WORK="$(mktemp -d "$BACKUP_DIR/.fitintel_backup_${TS}_XXXXXX")"
trap 'rm -rf "$WORK"; rm -f "$TMP_OUT"; docker compose -f "$COMPOSE_FILE" exec -T api rm -f "$ACCOUNTING_TMP" >/dev/null 2>&1 || true' EXIT

mkdir -p "$WORK/settings"

# 1. PostgreSQL: логин, пароль и имя БД остаются внутри контейнера.
docker compose -f "$COMPOSE_FILE" exec -T db \
    sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$WORK/database.sql.gz"
gzip -t "$WORK/database.sql.gz"

# 2. Accounting SQLite: согласованный online-backup работающей базы.
docker compose -f "$COMPOSE_FILE" exec -T api rm -f "$ACCOUNTING_TMP"
docker compose -f "$COMPOSE_FILE" exec -T api python -c \
    'import sqlite3; source = sqlite3.connect("'"$ACCOUNTING_DB"'"); target = sqlite3.connect("'"$ACCOUNTING_TMP"'"); source.backup(target); target.close(); source.close()'
docker compose -f "$COMPOSE_FILE" exec -T api cat "$ACCOUNTING_TMP" > "$WORK/accounting.sqlite"
docker compose -f "$COMPOSE_FILE" exec -T api rm -f "$ACCOUNTING_TMP"
[ "$(head -c 15 "$WORK/accounting.sqlite")" = "SQLite format 3" ] || {
    echo "$(date '+%F %T') backup ERROR: повреждён accounting.sqlite" >&2
    exit 1
}

# 3. Все постоянные файлы API, включая Docker-тома и файлы лицензии.
docker compose -f "$COMPOSE_FILE" exec -T api sh -c '
    set -e
    list=""
    for path in app/static srv/media app/data/face_photos app/.license_key app/.license_state; do
        [ ! -e "/$path" ] || list="$list $path"
    done
    [ -n "$list" ]
    tar -cf - -C / $list
' | gzip > "$WORK/files.tar.gz"
gzip -t "$WORK/files.tar.gz"

# 4. Настройки и секреты. Значения никогда не выводятся в журнал.
cp -a "$BASE/deploy/.env" "$WORK/settings/deploy.env"
cp -a "$SECRETS_DIR" "$WORK/settings/fitintel-secrets"
(crontab -l 2>/dev/null || true) > "$WORK/settings/crontab.txt"
for OPTIONAL in \
    "$BASE/deploy/nginx/ssl" \
    "$BASE/deploy/platform/.env" \
    "$BASE/deploy/platform/secrets" \
    "$BASE/deploy/platform/nginx/certs" \
    "$BASE/fitintel-desktop/client_settings.json" \
    "$BASE/fitintel-desktop/connections.json" \
    "$BASE/app/.license_key" \
    "$BASE/app/.license_state"; do
    if [ -e "$OPTIONAL" ]; then
        cp -a "$OPTIONAL" "$WORK/settings/"
    fi
done

{
    echo "FitIntel Pro full backup"
    echo "Created: $(date --iso-8601=seconds)"
    echo "Git commit: $(git -C "$BASE" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "Compose: $(basename "$COMPOSE_FILE")"
    echo "Contents: PostgreSQL dump; accounting SQLite online backup; API files/volumes; license; settings and secrets"
} > "$WORK/MANIFEST.txt"

# Готовый архив появляется только после успешной сборки и проверки.
tar -czf "$TMP_OUT" -C "$WORK" .
tar -tzf "$TMP_OUT" >/dev/null
[ -s "$TMP_OUT" ] || { echo "$(date '+%F %T') backup ERROR: пустой архив" >&2; exit 1; }
mv "$TMP_OUT" "$OUT"

find "$BACKUP_DIR" -type f \( -name 'fitintel_full_*.tar.gz' -o -name 'fitintel_*.sql.gz' \) \
    -mtime "+$RETENTION_DAYS" -delete
rm -rf "$WORK"
trap - EXIT
echo "$(date '+%F %T') full backup OK: $OUT ($(du -h "$OUT" | cut -f1))"
