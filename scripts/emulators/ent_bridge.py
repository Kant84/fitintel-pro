import os
# ЭНТ (Firebird) -> FitIntel: мост событий СКУД (v2: JWT для /visits)
import time, json, base64, urllib.request, urllib.error
import firebird.driver as fb

DB = "192.168.101.11:C:\\Program Files\\ENT\\Server\\DB\\CBASE.FDB"
FIT = "http://192.168.101.182/api/v1"
BASIC = "Basic " + base64.b64encode(b"itc:itc_secret_2026").decode()
ADMIN = {"login": "admin", "password": "Admin123!ChangeMe"}

def http(m, u, p=None, auth=None):
    req = urllib.request.Request(u, data=json.dumps(p).encode() if p else None,
                                 headers={"Content-Type": "application/json"}, method=m)
    if auth: req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            b = r.read().decode(); return r.status, json.loads(b) if b else {}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return None, str(e)

# JWT админа для /visits (с ретраями)
JWT = None
for _ in range(10):
    st, tok = http("POST", FIT + "/auth/login", ADMIN)
    if st == 200 and isinstance(tok, dict) and tok.get("access_token"):
        JWT = "Bearer " + tok["access_token"]
        print("JWT получен", flush=True)
        break
    print("ожидание FitIntel...", st, flush=True)
    time.sleep(10)
if not JWT:
    raise SystemExit("FitIntel не отвечает")

con = fb.connect(DB, user=os.environ["ENT_DB_USER"], password=os.environ["ENT_DB_PASSWORD"])
cur = con.cursor()
cur.execute("SELECT MAX(ID) FROM FB_EVN")
last_id = cur.fetchone()[0] or 0
print(f"МОСТ v2 ЗАПУЩЕН: старт с ID={last_id}. Подносите карту!", flush=True)

while True:
    try:
        cur.execute("SELECT ID, DT, DVS, EKEYH FROM FB_EVN WHERE ID > ? AND EVN = 2 AND EKEY <> 0 ORDER BY ID", (last_id,))
        rows = cur.fetchall()
        con.commit()
    except Exception as e:
        print("ошибка FB:", str(e)[:120], flush=True)
        time.sleep(3); continue
    for (eid, dt, dvs, ekeyh) in rows:
        uid = (ekeyh or "")[-8:]
        last_id = max(last_id, eid)
        st, resp = http("POST", FIT + "/skud/checkaccess",
                        {"device_id": "ent-" + dvs, "client_card": uid,
                         "request_id": str(eid), "direction": "entry"}, BASIC)
        grant = resp.get("grant_access") if isinstance(resp, dict) else None
        print(f"[{dt}] карта {uid} -> HTTP {st} grant={grant}", flush=True)
        if grant == 1 and isinstance(resp, dict) and resp.get("client_id"):
            st2, r2 = http("POST", FIT + "/visits/manual",
                           {"client_id": resp["client_id"], "entry_time": dt.isoformat(),
                            "access_method": "RFID", "zone": "ENT", "notes": "ЭНТ bridge evt " + str(eid)}, JWT)
            print(f"    -> визит: HTTP {st2}", flush=True)
            if st2 == 401:  # токен протух — обновим
                st3, tok = http("POST", FIT + "/auth/login", ADMIN)
                if st3 == 200: JWT = "Bearer " + tok["access_token"]
    time.sleep(2)