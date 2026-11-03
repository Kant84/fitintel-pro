#!/usr/bin/env bash
# FitIntel Pro — закрытие доступа к установке ПО (idempotent).
# Запуск после git clone:  sudo bash scripts/secure_install.sh [каталог-проекта]
set -Eeuo pipefail
DIR="${1:-$(pwd)}"
GROUP="admin.platform"
USER_NAME="$(stat -c '%U' "$DIR")"

echo "Каталог: $DIR | Пользователь: $USER_NAME | Группа: $GROUP"

if ! getent group "$GROUP" >/dev/null 2>&1; then
    groupadd "$GROUP" && echo "Создана группа: $GROUP"
fi
if ! id -nG "$USER_NAME" | tr ' ' '\n' | grep -qx "$GROUP"; then
    usermod -aG "$GROUP" "$USER_NAME" && echo "$USER_NAME добавлен в $GROUP"
fi

chown -R "$USER_NAME:$GROUP" "$DIR"
find "$DIR" -type d -exec chmod 750 {} +
find "$DIR" -type f -exec chmod 640 {} +
[ -f "$DIR/deploy/.env" ] && chmod 600 "$DIR/deploy/.env"

echo "--- Члены группы docker (доступ = root, проверьте лишних!) ---"
getent group docker || true
echo "SECURE_OK=1"
