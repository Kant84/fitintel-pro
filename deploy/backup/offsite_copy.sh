#!/usr/bin/env bash
set -euo pipefail
SRC=/home/andrei/fitintel-pro/deploy/backups
DST=andrei@192.168.101.125:/home/andrei/fitintel-backups
ssh andrei@192.168.101.125 'mkdir -p /home/andrei/fitintel-backups'
LATEST=$(ls -t "$SRC"/fitintel_full_*.tar.gz | head -1)
scp -q "$LATEST" "$DST/"
ssh andrei@192.168.101.125 'ls -t /home/andrei/fitintel-backups/fitintel_full_*.tar.gz | tail -n +8 | xargs -r rm -f'
echo "$(date '+%F %T') offsite OK: $(basename "$LATEST")"
