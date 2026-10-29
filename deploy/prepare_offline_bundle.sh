#!/usr/bin/env bash
# FitIntel Pro — offline bundle builder
set -Eeuo pipefail

# Собирает офлайн-пакет образов для install_prod.sh --offline.
# Использование: bash deploy/prepare_offline_bundle.sh [каталог_назначения]
# Требует интернет и Docker.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
OUT_DIR="${1:-$ROOT_DIR/offline-bundle}"
IMAGES_DIR="$OUT_DIR/offline-images"

cd "$ROOT_DIR"

if [ "${EUID}" -eq 0 ]; then
    echo "Run as a regular user with docker access, not root" >&2
    exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose v2 is required" >&2; exit 1; }

if [ ! -f "$ENV_FILE" ]; then
    python3 "$SCRIPT_DIR/generate_env.py"         --template "$SCRIPT_DIR/env.example"         --output "$ENV_FILE" >/dev/null
    GENERATED_ENV=1
else
    GENERATED_ENV=0
fi

echo "Building fitintel:prod..."
docker build -t fitintel:prod "$ROOT_DIR"

mkdir -p "$IMAGES_DIR"
docker save fitintel:prod -o "$IMAGES_DIR/fitintel-prod.tar"

echo "Collecting infrastructure images..."
mapfile -t IMAGES < <(docker compose --env-file "$ENV_FILE"     -f "$COMPOSE_FILE" config --images | sort -u | grep -v '^fitintel:prod$')

if [ "${#IMAGES[@]}" -eq 0 ]; then
    echo "No infrastructure images found in compose config" >&2
    exit 1
fi

for img in "${IMAGES[@]}"; do
    echo "Pulling $img"
    docker pull "$img" >/dev/null
    safe_name="$(echo "$img" | tr '/:@' '___')"
    docker save "$img" -o "$IMAGES_DIR/$safe_name.tar"
done

cat > "$OUT_DIR/README.txt" <<EOF
FitIntel Pro offline bundle
===========================
Составляющая кода: чистый git clone репозитория (см. docs/INSTALL_SERVER.md).
Установка:
  1. Скопируйте каталог offline-images в deploy/ репозитория
     (либо задайте FITINTEL_OFFLINE_DIR).
  2. sudo bash deploy/install_prod.sh --offline
Подготовлено: $(date -Is)
EOF

[ "$GENERATED_ENV" -eq 1 ] && rm -f "$ENV_FILE"

echo "OFFLINE_BUNDLE_READY=$OUT_DIR"
du -sh "$IMAGES_DIR"
ls -la "$IMAGES_DIR"
