#!/usr/bin/env bash
# Установка systemd timer для полного backup; cron fallback остаётся в install_cron.sh.
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$BASE/deploy/backup/backup.sh"
COMPOSE_FILE="${FITINTEL_COMPOSE_FILE:-$BASE/deploy/docker-compose.prod.yml}"
MARKER="deploy/backup/backup.sh"
SERVICE_TEMPLATE="$BASE/deploy/backup/fitintel-backup.service"
TIMER_TEMPLATE="$BASE/deploy/backup/fitintel-backup.timer"
SERVICE_TMP="$(mktemp)"
CRON_TMP="$(mktemp)"
trap 'rm -f "$SERVICE_TMP" "$CRON_TMP"' EXIT

for COMMAND in systemctl install mktemp; do
    command -v "$COMMAND" >/dev/null 2>&1 || {
        echo "backup install ERROR: команда $COMMAND не найдена" >&2
        exit 1
    }
done
for FILE in "$SCRIPT" "$COMPOSE_FILE" "$SERVICE_TEMPLATE" "$TIMER_TEMPLATE"; do
    [ -f "$FILE" ] || { echo "backup install ERROR: не найден $FILE" >&2; exit 1; }
done
case "$SCRIPT$COMPOSE_FILE" in
    *'"'*|*$'\n'*) echo "backup install ERROR: недопустимый путь" >&2; exit 1 ;;
esac

SUDO=()
if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null 2>&1 || { echo "backup install ERROR: нужен sudo" >&2; exit 1; }
    sudo -v
    SUDO=(sudo)
fi
chmod +x "$SCRIPT"

SERVICE_CONTENT="$(<"$SERVICE_TEMPLATE")"
SERVICE_CONTENT="${SERVICE_CONTENT//__FITINTEL_BACKUP_SCRIPT__/$SCRIPT}"
SERVICE_CONTENT="${SERVICE_CONTENT//__FITINTEL_COMPOSE_FILE__/$COMPOSE_FILE}"
printf '%s\n' "$SERVICE_CONTENT" > "$SERVICE_TMP"
"${SUDO[@]}" install -m 0644 "$SERVICE_TMP" /etc/systemd/system/fitintel-backup.service
"${SUDO[@]}" install -m 0644 "$TIMER_TEMPLATE" /etc/systemd/system/fitintel-backup.timer
"${SUDO[@]}" systemctl daemon-reload
"${SUDO[@]}" systemctl enable fitintel-backup.timer
"${SUDO[@]}" systemctl restart fitintel-backup.timer

# Удаляем только прежние FitIntel-задания; остальные строки сохраняются.
if command -v crontab >/dev/null 2>&1; then
    (crontab -l 2>/dev/null || true) | grep -vF "$MARKER" > "$CRON_TMP" || true
    if [ "$(id -u)" -ne 0 ]; then
        crontab "$CRON_TMP"
        (sudo crontab -l 2>/dev/null || true) | grep -vF "$MARKER" > "$CRON_TMP" || true
        sudo crontab "$CRON_TMP"
    else
        crontab "$CRON_TMP"
    fi
fi

systemctl is-active --quiet fitintel-backup.timer
printf 'systemd timer OK: ежедневно 21:30 и через 60 секунд после загрузки VM\n'
systemctl list-timers fitintel-backup.timer --no-pager
