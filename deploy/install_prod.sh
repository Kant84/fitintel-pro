#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"

cd "$ROOT_DIR"

if [ "${EUID}" -ne 0 ]; then
    echo "Run the production installer with sudo" >&2
    exit 1
fi

for command_name in docker python3; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command is missing: $command_name" >&2
        exit 1
    fi
done

if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 is required" >&2
    exit 1
fi

if [ -L "$ENV_FILE" ]; then
    echo "Refusing to use a symlink as deploy/.env" >&2
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    python3 "$SCRIPT_DIR/generate_env.py" \
        --template "$SCRIPT_DIR/env.example" \
        --output "$ENV_FILE"
else
    echo "EXISTING_PRODUCTION_ENV_PRESERVED=1"
fi
chmod 600 "$ENV_FILE"

python3 - "$ENV_FILE" <<'PY'
import sys
from pathlib import Path

values = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8-sig").splitlines():
    if line and not line.startswith("#") and "=" in line:
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()

for name in ("SECRET_KEY", "POSTGRES_PASSWORD"):
    value = values.get(name, "")
    normalized = value.casefold()
    markers = (
        "changeme", "change-me", "default", "example",
        "password", "secret", "test",
    )
    minimum = 32 if name == "SECRET_KEY" else 12
    if len(value) < minimum or any(marker in normalized for marker in markers):
        raise RuntimeError(f"{name} is missing, weak, or placeholder-like")

if values.get("APP_ENV") != "prod":
    raise RuntimeError("APP_ENV must be prod")

print("PRODUCTION_ENV_PREFLIGHT_OK=1")
PY

compose() {
    docker compose \
        --env-file "$ENV_FILE" \
        -f "$COMPOSE_FILE" \
        "$@"
}

for volume_name in     deploy_static_trainers     deploy_static_products     deploy_static_scan     deploy_clients_data     deploy_media_data     deploy_accounting_data
do
    docker volume create "$volume_name" >/dev/null
done

MEDIA_SECRET_FILE="/etc/fitintel/secrets/media_master_key"
install -d -m 700 -o root -g root /etc/fitintel/secrets
if [ -L "$MEDIA_SECRET_FILE" ]; then
    echo "Refusing to use a symlink as media_master_key" >&2
    exit 1
fi
if [ ! -f "$MEDIA_SECRET_FILE" ]; then
    python3 - "$MEDIA_SECRET_FILE" <<'PY'
import base64
import os
import sys

fd = os.open(
    sys.argv[1],
    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
    0o600,
)
with os.fdopen(fd, "wb") as stream:
    stream.write(base64.b64encode(os.urandom(32)))
    stream.write(bytes([10]))
PY
fi
chmod 600 "$MEDIA_SECRET_FILE"
echo "PRODUCTION_RUNTIME_RESOURCES_OK=1"

echo "Building FitIntel production image..."
docker build -t fitintel:prod .

echo "Pulling infrastructure images..."
compose pull db redis nginx

echo "Starting PostgreSQL and Redis..."
compose up -d db redis

database_ready=0
for attempt in $(seq 1 60); do
    if compose exec -T db sh -c \
        'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1'; then
        database_ready=1
        break
    fi
    sleep 2
done

if [ "$database_ready" -ne 1 ]; then
    echo "PostgreSQL did not become ready" >&2
    exit 1
fi
health_path="/api/v1/health/"

echo "Running Alembic migrations..."
compose run --rm --no-deps api alembic upgrade head

echo "Seeding roles and permissions..."
compose run --rm api python -c '
from app.db.session import SessionLocal
from app.db.seed.seed_permissions import seed_permissions
from app.db.seed.seed_roles import seed_roles

db = SessionLocal()
try:
    seed_permissions(db)
    seed_roles(db)
    db.commit()
finally:
    db.close()
'

echo "Create the initial FitIntel administrator."

while true; do
    read -r -p "Login (email): " FITINTEL_ADMIN_USERNAME
    case "$FITINTEL_ADMIN_USERNAME" in
        *@*.*)
            break
            ;;
        *)
            echo "Login must be a valid email address."
            ;;
    esac
done

FITINTEL_ADMIN_EMAIL="$FITINTEL_ADMIN_USERNAME"

while true; do
    read -r -s -p "Password: " FITINTEL_ADMIN_PASSWORD
    echo
    read -r -s -p "Confirm password: " password_confirmation
    echo

    if [ "${#FITINTEL_ADMIN_PASSWORD}" -lt 8 ]; then
        echo "Password must contain at least 8 characters."
        unset FITINTEL_ADMIN_PASSWORD password_confirmation
        continue
    fi

    if [ "$FITINTEL_ADMIN_PASSWORD" != "$password_confirmation" ]; then
        echo "Passwords do not match."
        unset FITINTEL_ADMIN_PASSWORD password_confirmation
        continue
    fi

    unset password_confirmation
    break
done

export FITINTEL_ADMIN_EMAIL
export FITINTEL_ADMIN_USERNAME
export FITINTEL_ADMIN_PASSWORD

if ! compose run --rm \
    -e FITINTEL_ADMIN_EMAIL \
    -e FITINTEL_ADMIN_USERNAME \
    -e FITINTEL_ADMIN_PASSWORD \
    api python -m scripts.create_admin; then
    unset FITINTEL_ADMIN_EMAIL FITINTEL_ADMIN_USERNAME FITINTEL_ADMIN_PASSWORD
    echo "Initial administrator registration failed" >&2
    exit 1
fi

unset FITINTEL_ADMIN_EMAIL FITINTEL_ADMIN_USERNAME FITINTEL_ADMIN_PASSWORD
echo "INITIAL_ADMIN_REGISTRATION_COMPLETED=1"

echo "Starting all production services..."
compose up -d

api_ready=0
for attempt in $(seq 1 60); do
    if compose exec -T api python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000$health_path', timeout=5)" \
        >/dev/null 2>&1; then
        api_ready=1
        break
    fi
    sleep 2
done

if [ "$api_ready" -ne 1 ]; then
    echo "API health check failed" >&2
    exit 1
fi

chown -R root:root "$ROOT_DIR"
chmod 750 "$ROOT_DIR"
chmod 700 "$SCRIPT_DIR"
echo "INSTALL_DIRECTORY_PROTECTED=1"

echo "PRODUCTION_INSTALL_COMPLETED=1"
echo "NEXT_STEP=Activate the club license and complete the protected web setup"
