# ЭНТ (Firebird) -> FitIntel: мост событий СКУД
import time, json, base64, urllib.request, urllib.error
import firebird.driver as fb

DB = "192.168.101.11:C:\\Program Files\\ENT\\Server\\DB\\CBASE.FDB"
FIT = "http://192.168.101.182/api/v1"
AUTH = "Basic " + base64.b64encode(b"itc:itc_secret_2026").decode()

def http(method, url, payload=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                                 headers={"Content-Type": "application/json"}, method=method)
    req.add_header("Authorization", AUTH)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode()
            return r.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return None, str(e)

con = fb.connect(DB, user="SYSDBA", password="masterkey")
cur = con.cursor()
cur.execute("SELECT MAX(ID) FROM FB_EVN")
last_id = cur.fetchone()[0] or 0
print(f"МОСТ ЗАПУЩЕН: старт с ID={last_id}. Подносите карту!", flush=True)

while True:
    try:
        cur.execute("SELECT ID, DT, DVS, EKEYH FROM FB_EVN WHERE ID > ? AND EVN = 2 AND EKEY <> 0 ORDER BY ID", (last_id,))
        rows = cur.fetchall()
        con.commit()
    except Exception as e:
        print("ошибка FB:", str(e)[:120], flush=True)
        time.sleep(3)
        continue
    for (eid, dt, dvs, ekeyh) in rows:
        uid = (ekeyh or "")[-8:]
        last_id = max(last_id, eid)
        st, resp = http("POST", FIT + "/skud/checkaccess",
                        {"device_id": "ent-" + dvs, "client_card": uid,
                         "request_id": str(eid), "direction": "entry"})
        grant = resp.get("grant_access") if isinstance(resp, dict) else None
        print(f"[{dt}] карта {uid} -> FitIntel: HTTP {st} grant={grant} | {resp}", flush=True)
        if grant == 1 and isinstance(resp, dict) and resp.get("client_id"):
            st2, r2 = http("POST", FIT + "/visits/manual",
                           {"client_id": resp["client_id"], "entry_time": dt.isoformat(),
                            "access_method": "RFID", "zone": "ENT-bridge",
                            "notes": "Авто: ЭНТ bridge, событие " + str(eid)})
            print(f"    -> визит создан: HTTP {st2}", flush=True)
    time.sleep(2)
