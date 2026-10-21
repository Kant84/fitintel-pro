#!/usr/bin/env bash
# Провижининг моста событий для клуба. Запуск: sudo bash provision_bridge.sh
set -e
ENV=/etc/fitintel/bridge.env
FIT="http://192.168.101.182/api/v1"
echo "=== Провижининг моста СКУД -> FitIntel (v4) ==="
read -s -p "Пароль superadmin клуба: " SA; echo
TOK=$(curl -s -L -X POST $FIT/auth/login -H 'Content-Type: application/json' -d "{\"login\":\"superadmin\",\"password\":\"$SA\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')
[ -n "$TOK" ] || { echo "вход не удался"; exit 1; }
PW=$(python3 -c 'import secrets;print(secrets.token_urlsafe(18))')
RESP=$(curl -s -L -w "\n%{http_code}" -X POST $FIT/users/ -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d "{\"username\":\"bridge\",\"email\":\"bridge@fitintel.ru\",\"password\":\"$PW\",\"role\":\"device\"}")
CODE=$(echo "$RESP" | tail -1)
echo "пользователь bridge -> HTTP $CODE"
OLD_PW=""
[ -f "$ENV" ] && OLD_PW=$(grep '^password=' "$ENV" | head -1 | cut -d= -f2-)
case "$CODE" in
  200|201) WRITE_PW=1 ;;
  409)
    if [ -n "$OLD_PW" ] && python3 -c "
import json,urllib.request,sys
c=dict(l.split('=',1) for l in open('$ENV') if '=' in l)
req=urllib.request.Request('$FIT/auth/login',data=json.dumps({'login':'bridge','password':c.get('password','')}).encode(),headers={'Content-Type':'application/json'})
try:
    sys.exit(0 if urllib.request.urlopen(req,timeout=8).status==200 else 1)
except Exception:
    sys.exit(1)"; then
      echo "bridge уже существует и пароль из env подходит — НЕ перезаписываю"
      WRITE_PW=0
    else
      echo "ПОЛОМАНО: пользователь bridge существует, но пароль неизвестен."
      echo "Удалите его и перезапустите скрипт:"
      echo "  TOK=...; curl -X DELETE $FIT/users/<id> -H "Authorization: Bearer \$TOK""
      exit 1
    fi ;;
  *) echo "$RESP"; exit 1 ;;
esac
echo "Режим источника событий: fb | http | file | none"
read -p "MODE [none]: " MODE; MODE=${MODE:-none}
sudo mkdir -p /etc/fitintel
{
  [ "$WRITE_PW" = "1" ] && echo "password=$PW" || echo "password=$OLD_PW"
  echo "login=bridge"; echo "fit=$FIT"; echo "mode=$MODE"
  if [ "$MODE" = "fb" ]; then
    read -p "Хост Firebird: " FBH
    read -p "Путь к базе: " FBP
    read -p "Пользователь FB [SYSDBA]: " FBU; FBU=${FBU:-SYSDBA}
    read -s -p "Пароль FB [masterkey]: " FBPW; echo; FBPW=${FBPW:-masterkey}
    echo "db=$FBH:$FBP"; echo "fb_user=$FBU"; echo "fb_password=$FBPW"
  fi
  if [ "$MODE" = "http" ]; then
    read -p "URL событий: " U; echo "http_url=$U"
    read -p "Интервал опроса, сек [10]: " I; echo "http_interval=${I:-10}"
  fi
  if [ "$MODE" = "file" ]; then
    read -p "Каталог очереди [/var/spool/fitintel-events]: " D; echo "file_dir=${D:-/var/spool/fitintel-events}"
  fi
  echo "itc_user=itc"; echo "itc_password=itc_secret_2026"
} | sudo tee $ENV > /dev/null
sudo chmod 600 $ENV
echo "OK. sudo systemctl restart ent_bridge.service"
