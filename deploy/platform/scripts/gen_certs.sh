#!/usr/bin/env bash
# Генерация CA, серверного и клиентского сертификатов (mTLS) для платформы.
# Запуск: bash scripts/gen_certs.sh <admin_email> [EXTRA_IP]
#   EXTRA_IP — дополнительный SAN (например LAN-IP сервера). Публичный IP берётся из .env (PUBLIC_IP).
set -e
cd "$(dirname "$0")/.."
PUBLIC_IP="$(grep '^PUBLIC_IP=' .env | cut -d= -f2)"
[ -z "$PUBLIC_IP" ] && { echo "PUBLIC_IP не задан в .env"; exit 1; }
EXTRA_SAN="${2:+,IP:$2}"
cd nginx/certs

[ -f ca.key ] && { echo "CA уже существует (ca.key). Для перевыпуска удалите certs/ca.*"; exit 1; }

# 1) CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/CN=FitIntel Platform CA"

# 2) Серверный сертификат (openssl 1.1: -extfile вместо -addext)
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=fitintel-platform"
printf "subjectAltName=IP:%s,IP:127.0.0.1%s\n" "$PUBLIC_IP" "$EXTRA_SAN" > ext_server.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -extfile ext_server.cnf

# 3) Клиентский сертификат админа
ADMIN_EMAIL="${1:-admin@fitintel.local}"
openssl genrsa -out "client_${ADMIN_EMAIL}.key" 2048
openssl req -new -key "client_${ADMIN_EMAIL}.key" -out client.csr -subj "/CN=${ADMIN_EMAIL}"
printf "extendedKeyUsage=clientAuth\n" > ext_client.cnf
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out "client_${ADMIN_EMAIL}.crt" -days 825 -sha256 -extfile ext_client.cnf

rm -f server.csr client.csr ext_server.cnf ext_client.cnf
echo "Готово: CA, server.crt (SAN: $PUBLIC_IP, 127.0.0.1$EXTRA_SAN), client_${ADMIN_EMAIL}.*"
