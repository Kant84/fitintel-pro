#!/usr/bin/env bash
# Установка/обновление расписания production-бэкапов; остальные задания сохраняются.
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$BASE/deploy/backup/backup.sh"
LOG="$BASE/deploy/backup/backup.log"
MARKER="deploy/backup/backup.sh"
LOCK="/tmp/fitintel-backup.lock"

for COMMAND in crontab flock docker; do
    if ! command -v "$COMMAND" >/dev/null 2>&1; then
        echo "backup install ERROR: команда $COMMAND не найдена" >&2
        exit 1
    fi
done

chmod +x "$SCRIPT"
FLOCK="$(command -v flock)"
SLEEP="$(command -v sleep)"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# Удаляем только прежние строки FitIntel backup; media-backup и другие задачи не трогаем.
(crontab -l 2>/dev/null || true) | grep -vF "$MARKER" > "$TMP" || true
{
    echo "30 21 * * * $FLOCK -n $LOCK $SCRIPT >> $LOG 2>&1"
    echo "@reboot $SLEEP 60 && $FLOCK -n $LOCK $SCRIPT >> $LOG 2>&1"
} >> "$TMP"
crontab "$TMP"

printf 'cron OK: ежедневно 21:30 и после перезагрузки VM -> %s\n' "$SCRIPT"
printf 'backup dir: %s\n' "$BASE/deploy/backups"
