#!/usr/bin/env bash
# Установка полного backup: root-cron используется только для root-only секретов.
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$BASE/deploy/backup/backup.sh"
LOG="$BASE/deploy/backup/backup.log"
MARKER="deploy/backup/backup.sh"
LOCK="/tmp/fitintel-backup.lock"
if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
    exec bash "$BASE/deploy/backup/install_systemd.sh"
fi
SECRETS_DIR="${FITINTEL_SECRETS_DIR:-/etc/fitintel/secrets}"
CRON_SCOPE="user"

for COMMAND in crontab flock docker; do
    command -v "$COMMAND" >/dev/null 2>&1 || {
        echo "backup install ERROR: команда $COMMAND не найдена" >&2
        exit 1
    }
done

chmod +x "$SCRIPT"

if [ "$(id -u)" -eq 0 ]; then
    CRON_SCOPE="root"
elif [ -d "$SECRETS_DIR" ] && [ ! -r "$SECRETS_DIR/media_master_key" ]; then
    command -v sudo >/dev/null 2>&1 || {
        echo "backup install ERROR: нужен sudo для чтения защищённых секретов" >&2
        exit 1
    }
    sudo -v
    CRON_SCOPE="root"
fi

cron() {
    if [ "$CRON_SCOPE" = "root" ] && [ "$(id -u)" -ne 0 ]; then
        sudo crontab "$@"
    else
        crontab "$@"
    fi
}

FLOCK="$(command -v flock)"
SLEEP="$(command -v sleep)"
TMP="$(mktemp)"
USER_TMP="$(mktemp)"
trap 'rm -f "$TMP" "$USER_TMP"' EXIT

(cron -l 2>/dev/null || true) | grep -vF "$MARKER" > "$TMP" || true
{
    echo "30 21 * * * $FLOCK -n $LOCK $SCRIPT >> $LOG 2>&1"
    echo "@reboot $SLEEP 60 && $FLOCK -n $LOCK $SCRIPT >> $LOG 2>&1"
} >> "$TMP"
cron "$TMP"

# После переноса в root-cron удаляем только старые FitIntel-задания пользователя.
if [ "$CRON_SCOPE" = "root" ] && [ "$(id -u)" -ne 0 ]; then
    (crontab -l 2>/dev/null || true) | grep -vF "$MARKER" > "$USER_TMP" || true
    crontab "$USER_TMP"
fi

printf 'cron OK (%s): ежедневно 21:30 и после перезагрузки VM -> %s\n' "$CRON_SCOPE" "$SCRIPT"
printf 'backup dir: %s\n' "$BASE/deploy/backups"
