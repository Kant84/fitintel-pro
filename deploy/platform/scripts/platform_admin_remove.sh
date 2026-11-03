#!/usr/bin/env bash
# Отзыв администратора платформы: CN из ADMIN_CNS + restart api + CRL-отзыв сертификата
# Запуск: bash scripts/platform_admin_remove.sh email@domain
set -e
cd "$(dirname "$0")/.."
EMAIL="${1:?укажите email}"
CUR=$(grep '^ADMIN_CNS=' .env | cut -d= -f2-)
NEW=$(echo "$CUR" | tr ',' '\n' | grep -vFx "$EMAIL" | paste -sd, -)
sed -i "s/^ADMIN_CNS=.*/ADMIN_CNS=${NEW}/" .env
docker compose up -d platform_api
cd nginx/certs
if [ -f "client_${EMAIL}.crt" ]; then
  SERIAL=$(openssl x509 -in "client_${EMAIL}.crt" -noout -serial | cut -d= -f2)
  grep -v "$SERIAL" index.txt > index.tmp 2>/dev/null || true
  printf "R\t260101000000Z\t%s\t%s\tunknown\t/CN=%s\n" "$(date +%y%m%d%H%M%SZ)" "$SERIAL" "$EMAIL" >> index.tmp
  mv index.tmp index.txt
  sort -t "$(printf '\t')" -k2 -o index.txt index.txt
  openssl ca -gencrl -config ca.cnf -out ca.crl
  rm -f "client_${EMAIL}.crt" "client_${EMAIL}.key" "client_${EMAIL}.p12"
  echo "сертификат отозван (CRL обновлён)"
fi
cd ../..
docker compose restart nginx
echo "=== отозвано: ${EMAIL} ==="
