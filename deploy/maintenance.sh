#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
ACTION="${1:-}"

cd "$ROOT_DIR"

if [ "${EUID}" -ne 0 ]; then
    echo "Run FitIntel maintenance with sudo" >&2
    exit 1
fi

case "$ACTION" in
    status|health|backup)
        ;;
    *)
        echo "Usage: sudo bash deploy/maintenance.sh status|health|backup" >&2
        exit 2
        ;;
esac

compose() {
    docker compose \
        --env-file "$ENV_FILE" \
        -f "$COMPOSE_FILE" \
        "$@"
}

echo "FitIntel server administrator authorization is required."

# Логин и пароль запрашиваются интерактивно внутри контейнера.
# Пароль не передаётся аргументом и не попадает в командную строку.
if ! compose run --rm -it api python -m scripts.server_admin login; then
    echo "SERVER_MAINTENANCE_AUTH_FAILED=1" >&2
    exit 1
fi

case "$ACTION" in
    status)
        compose ps
        echo "SERVER_MAINTENANCE_STATUS_OK=1"
        ;;

    health)
        compose exec -T api python -c \
            "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health/', timeout=5).read().decode())"
        echo "SERVER_MAINTENANCE_HEALTH_OK=1"
        ;;

    backup)
        umask 077
        BACKUP_DIR="/root/fitintel-backups"
        BACKUP="$BACKUP_DIR/maintenance-$(date +%Y%m%d-%H%M%S).dump"
        install -d -m 700 -o root -g root "$BACKUP_DIR"

        if ! compose exec -T db sh -c \
            'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
            > "$BACKUP"; then
            rm -f "$BACKUP"
            echo "SERVER_MAINTENANCE_BACKUP_FAILED=1" >&2
            exit 1
        fi

        if [ ! -s "$BACKUP" ]; then
            rm -f "$BACKUP"
            echo "SERVER_MAINTENANCE_BACKUP_EMPTY=1" >&2
            exit 1
        fi

        chmod 600 "$BACKUP"
        echo "SERVER_MAINTENANCE_BACKUP_OK=$BACKUP"
        ;;
esac