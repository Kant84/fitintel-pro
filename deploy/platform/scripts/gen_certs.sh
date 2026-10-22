#!/usr/bin/env bash
# Генерация CA, серверного и клиентских сертификатов (mTLS) для платформы.
# Запуск: bash scripts/gen_certs.sh [admin_email] — первый аргумент = email админа (клиентский сертификат).
set -e
cd "$(dirname "$0")/../nginx/certs"

[ -f ca.key ] && { echo "CA уже существует (ca.key). Для перевыпуска удалите certs/ca.*"; exit 1; }

# 1) CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/CN=FitIntel Platform CA"

# 2) Серверный сертификат (IP 79.174.46.68; при появлении домена добавьте admin.fitintel.ru в -addext)
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=fitintel-platform"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 \
  -addext "subjectAltName=IP:"$PUBLIC_IP",IP:127.0.0.1"$EXTRA_SAN""

# 3) Клиентский сертификат админа (первый)
PUBLIC_IP=$(grep "^PUBLIC_IP=" ../.env | cut -d= -f2)
EXTRA_SAN="${2:+,IP:$2}"
ADMIN_EMAIL="${1:-admin@fitintel.local}"
openssl genrsa -out "client_${ADMIN_EMAIL}.key" 2048
openssl req -new -key "client_${ADMIN_EMAIL}.key" -out client.csr -subj "/CN=${ADMIN_EMAIL}"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out "client_${ADMIN_EMAIL}.crt" -days 825 -sha256 -extfile <(printf "extendedKeyUsage=clientAuth")

# 4) Пустой CRL (обновляется при отзыве: см. README «Отзыв сертификата»)
printf '' > ca.crl.empty
openssl ca -gencrl -config <(printf "[ca]\ndefault_ca=CA\n[CA]\ndatabase=index.txt\nserial=serial\ndefault_md=sha256\ndefault_crl_days=30\ncertificate=ca.crt\nprivate_key=ca.key") -out ca.crl 2>/dev/null || touch ca.crl

rm -f server.csr client.csr
echo "Готово. Клиенту установить в браузер: client_${ADMIN_EMAIL}.p12:"
openssl pkcs12 -export -out "client_${ADMIN_EMAIL}.p12" \
  -inkey "client_${ADMIN_EMAIL}.key" -in "client_${ADMIN_EMAIL}.crt" -certfile ca.crt
echo "certs/client_${ADMIN_EMAIL}.p12 (импорт в браузер/ОС, пароль при желании)"
