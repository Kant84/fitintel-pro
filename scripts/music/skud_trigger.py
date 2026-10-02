# -*- coding: utf-8 -*-
"""
Триггер «умный клуб»: считает входы по СКУД за окно; при превышении порога
шлёт POST /music/zones/{id}/energize (энерджи-плейлист + громкость 90).
Работает на VM рядом с docker (опрашивает БД через docker exec psql).

  --threshold N    сколько входов за окно включить energize (по умолчанию 10)
  --window-min N   окно подсчёта, минут (по умолчанию 60)
  --cooldown-min N повторный срабатывание не чаще, минут (по умолчанию 15)
  --once           один проход и выход (для теста)

Требует: доступ к БД через `docker exec deploy-db-1 psql` и curl к API.
"""
import argparse
import json
import subprocess
import time
import urllib.request

DEFAULT_ZONES = {
    # имя зоны музыки -> любой маркер (имя зоны СКУД/тип события) — расширяйте
    "Trenazhernyy zal": {"threshold": 10},
}


def count_entries(window_min):
    sql = ("SELECT count(*) FROM access_logs "
           "WHERE created_at > now() - interval '%d minutes'" % window_min)
    out = subprocess.run(
        ["docker", "exec", "deploy-db-1", "psql", "-U", "fitnexus_user",
         "-d", "fitnexus_ai", "-t", "-c", sql],
        capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError("psql: %s" % out.stderr.strip()[:200])
    return int(out.stdout.strip() or 0)


def energize(zone_id, server, token):
    body = json.dumps({}).encode()
    req = urllib.request.Request(
        server.rstrip("/") + "/music/zones/%s/energize" % zone_id,
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://localhost/api/v1")
    ap.add_argument("--token", required=True, help="admin token ( music-api без auth, но на будущее )")
    ap.add_argument("--threshold", type=int, default=10)
    ap.add_argument("--window-min", type=int, default=60)
    ap.add_argument("--cooldown-min", type=int, default=15)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=60)
    a = ap.parse_args()

    last_fire = {}   # zone_id -> timestamp
    print("SKUD-trigger | порог %s входов / %s мин | cooldown %s мин"
          % (a.threshold, a.window_min, a.cooldown_min))

    # id музыкальных зон local_agent
    with urllib.request.urlopen(a.server.rstrip("/") + "/music/zones", timeout=10) as r:
        zones = [z for z in json.load(r) if z["provider_type"] == "local_agent"]
    if not zones:
        print("SKUD-trigger | нет зон local_agent — выход")
        return

    while True:
        try:
            n = count_entries(a.window_min)
            print("SKUD-trigger | входов за %s мин: %s" % (a.window_min, n))
            if n >= a.threshold:
                for z in zones:
                    last = last_fire.get(z["id"], 0)
                    if time.time() - last < a.cooldown_min * 60:
                        continue
                    try:
                        res = energize(z["id"], a.server, a.token)
                        print("SKUD-trigger | ENERGIZE ->", z["name"], res)
                        last_fire[z["id"]] = time.time()
                    except Exception as e:
                        print("SKUD-trigger | energize FAIL:", e)
        except Exception as e:
            print("SKUD-trigger | ERR:", e)
        if a.once:
            break
        time.sleep(a.interval)


if __name__ == "__main__":
    main()