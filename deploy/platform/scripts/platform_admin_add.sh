#!/usr/bin/env bash
# Добавление администратора платформы: сертификат + CN в ADMIN_CNS + restart api
# Запуск: bash scripts/platform_admin_add.sh email@domain
set -e
cd "$(dirname "$0")/.."
EMAIL="${1:?укажите email: bash scripts/platform_admin_add.sh email@domain}"
[ -f "nginx/certs/client_${EMAIL}.crt" ] || bash scripts/gen_client.sh "$EMAIL" >/dev/null
if grep -q '^ADMIN_CNS=' .env 2>/dev/null; then
  CUR=$(grep '^ADMIN_CNS=' .env | cut -d= -f2-)
  case ",$CUR," in *",${EMAIL},"*) ;; *) sed -i "s/^ADMIN_CNS=.*/ADMIN_CNS=${CUR},${EMAIL}/" .env ;; esac
else
  echo "ADMIN_CNS=${EMAIL}" >> .env
fi
docker compose up -d platform_api
echo "=== готово ==="
echo "CN ${EMAIL} в ADMIN_CNS; api перезапущен"
echo "p12 для передачи: nginx/certs/client_${EMAIL}.p12 (см. PLATFORM_USER_GUIDE.md §1.3)"
