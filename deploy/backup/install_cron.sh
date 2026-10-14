#!/bin/bash
# Автоустановка расписания бэкапов. Вызывать при установке/обновлении ПО.
set -e
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$BASE/deploy/backup/backup.sh"
LOG="$BASE/deploy/backup/backup.log"
MARKER="deploy/backup/backup.sh"
(crontab -l 2>/dev/null | grep -v "$MARKER"; echo "30 3 * * * $SCRIPT >> $LOG 2>&1") | crontab -
echo "cron OK: ежедневный бэкап 03:30 -> $SCRIPT"
