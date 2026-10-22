#!/usr/bin/env bash
# Выпуск дополнительного клиентского сертификата (новый админ/поддержка).
# Запуск: bash scripts/gen_client.sh email@domain
set -e
cd "$(dirname "$0")/../nginx/certs"
EMAIL="${1:?укажите email: bash scripts/gen_client.sh email@domain}"
[ -f "client_${EMAIL}.crt" ] && { echo "уже существует: client_${EMAIL}.crt"; exit 1; }
openssl genrsa -out "client_${EMAIL}.key" 2048
openssl req -new -key "client_${EMAIL}.key" -out client.csr -subj "/CN=${EMAIL}"
printf "extendedKeyUsage=clientAuth\n" > ext_client.cnf
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out "client_${EMAIL}.crt" -days 825 -sha256 -extfile ext_client.cnf
rm -f client.csr ext_client.cnf
openssl pkcs12 -export -out "client_${EMAIL}.p12" \
  -inkey "client_${EMAIL}.key" -in "client_${EMAIL}.crt" -certfile ca.crt
echo "Готово: client_${EMAIL}.p12"
echo "Добавьте '${EMAIL}' в ADMIN_CNS (.env) и перезапустите platform_api."
