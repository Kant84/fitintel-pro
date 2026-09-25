#!/usr/bin/env bash
# Установка автобэкапа одной командой: bash scripts/backup/install_cron.sh
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v crontab >/dev/null 2>&1; then
  echo "crontab не найден. Установите:"
  echo "  sudo apt install -y cron && sudo systemctl enable --now cron"
  exit 1
fi

if [ ! -f "$DIR/backup.env" ]; then
  cp "$DIR/backup.env.example" "$DIR/backup.env"
  echo "Создан конфиг: $DIR/backup.env"
else
  echo "Конфиг уже есть: $DIR/backup.env"
fi
chmod +x "$DIR/backup.sh"

LINE="0 3 * * * $DIR/backup.sh $DIR/backup.env >> /var/log/fitintel-backup.log 2>&1"
if crontab -l 2>/dev/null | grep -qF "$DIR/backup.sh"; then
  echo "Cron-запись уже установлена — пропуск"
else
  ( crontab -l 2>/dev/null || true; echo "$LINE" ) | crontab -
  echo "Добавлено в cron: $LINE"
fi

echo ""
echo "Готово! Проверьте: crontab -l | grep backup"
echo "Тест: $DIR/backup.sh $DIR/backup.env"
