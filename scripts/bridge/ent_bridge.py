# СКУД -> FitIntel: универсальный мост событий v4
# Режим источника: MODE в /etc/fitintel/bridge.env = fb | http | file | none
import time, json, base64, os, glob, urllib.request, urllib.error

ENV = "/etc/fitintel/bridge.env"

def _cfg(k, d=""):
    try:
        for line in open(ENV, encoding="utf-8"):
            if line.startswith(k + "="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return d

MODE = _cfg("mode", "none")
FIT = _cfg("fit", "http://192.168.101.182/api/v1").rstrip("/")
BASIC = "Basic " + base64.b64encode((_cfg("itc_user", "itc") + ":" + _cfg("itc_password", "itc_secret_2026")).encode()).decode()
ADMIN = {"login": _cfg("login", "bridge"), "password": _cfg("password", "")}
STATE_FILE = _cfg("state_file", "/home/andrei/.bridge_state.json")

def _load():
    try:
        return json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        return {}

STATE = _load()

def _save(d):
    STATE.update(d)
    try:
        json.dump(STATE, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass

def http(m, u, p=None, auth=None):
    req = urllib.request.Request(u, data=json.dumps(p).encode() if p is not None else None,
                                 headers={"Content-Type": "application/json"}, method=m)
    if auth:
        req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            b = r.read().decode()
            return r.status, json.loads(b) if b else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return None, str(e)

JWT = None

def do_login():
    global JWT
    st, tok = http("POST", FIT + "/auth/login", ADMIN)
    if st == 200 and isinstance(tok, dict) and tok.get("access_token"):
        JWT = "Bearer " + tok["access_token"]
        _save({"tokens": {"access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", "")}})
        print("JWT получен (login)", flush=True)
        return True
    if st == 423:
        print("423 Locked — пауза 6 мин", flush=True)
        time.sleep(360)
    else:
        print("login не удался:", st, str(tok)[:120], flush=True)
        time.sleep(30)
    return False

def ensure_token():
    global JWT
    if JWT:
        return True
    rt = (STATE.get("tokens") or {}).get("refresh_token")
    if rt:
        st, r = http("POST", FIT + "/auth/refresh", {"refresh_token": rt})
        if st == 200 and isinstance(r, dict) and r.get("access_token"):
            JWT = "Bearer " + r["access_token"]
            _save({"tokens": {"access_token": r["access_token"], "refresh_token": r.get("refresh_token") or rt}})
            print("JWT обновлён (refresh)", flush=True)
            return True
    return do_login()

def process(eid, dt, device, uid):
    global JWT
    uid = (uid or "")[-8:]
    st, resp = http("POST", FIT + "/skud/checkaccess",
                    {"device_id": str(device), "client_card": uid,
                     "request_id": str(eid), "direction": "entry"}, BASIC)
    grant = resp.get("grant_access") if isinstance(resp, dict) else None
    print("[%s] карта %s -> HTTP %s grant=%s" % (dt, uid, st, grant), flush=True)
    if grant == 1 and isinstance(resp, dict) and resp.get("client_id"):
        st2, r2 = http("POST", FIT + "/visits/manual",
                       {"client_id": resp["client_id"], "entry_time": str(dt),
                        "access_method": "RFID", "zone": str(device)[:16],
                        "notes": "bridge evt " + str(eid)}, JWT)
        print("    -> визит: HTTP %s" % st2, flush=True)
        if st2 == 401:
            JWT = None
            ensure_token()

def run_fb():
    import firebird.driver as fb
    DB = _cfg("db", "")
    def conn():
        return fb.connect(DB, user=_cfg("fb_user", "SYSDBA"), password=_cfg("fb_password", "masterkey"))
    for _ in range(360):
        try:
            con = conn(); break
        except Exception as e:
            print("FB недоступен, жду 10 сек:", str(e)[:120], flush=True)
            time.sleep(10)
    else:
        raise SystemExit("Firebird недоступен")
    cur = con.cursor()
    last = STATE.get("last_id") or 0
    cur.execute("SELECT MAX(ID) FROM FB_EVN")
    last = max(last, cur.fetchone()[0] or 0)
    _save({"last_id": last})
    print("МОСТ v4 (fb) ЗАПУЩЕН: старт с ID=%s" % last, flush=True)
    while True:
        try:
            cur.execute("SELECT ID, DT, DVS, EKEYH FROM FB_EVN WHERE ID > ? AND EVN = 2 AND EKEY <> 0 ORDER BY ID", (last,))
            rows = cur.fetchall()
            con.commit()
        except Exception as e:
            print("ошибка FB (переподключение):", str(e)[:120], flush=True)
            time.sleep(5)
            try:
                con = conn(); cur = con.cursor()
            except Exception as e2:
                print("FB недоступен:", str(e2)[:120], flush=True)
                time.sleep(30)
            continue
        for (eid, dt, dvs, ekeyh) in rows:
            last = max(last, eid)
            process(eid, dt.isoformat(), "ent-" + str(dvs), ekeyh)
        if rows:
            _save({"last_id": last})
        time.sleep(2)

def run_http():
    url = _cfg("http_url", "")
    interval = int(_cfg("http_interval", "10"))
    last = STATE.get("last_id") or 0
    print("МОСТ v4 (http) ЗАПУЩЕН: %s, after_id=%s" % (url, last), flush=True)
    while True:
        sep = "&" if "?" in url else "?"
        st, r = http("GET", url + sep + "after_id=" + str(last))
        if st == 200 and isinstance(r, dict):
            for ev in r.get("events", []):
                try:
                    eid = int(ev.get("id"))
                except Exception:
                    continue
                if eid <= int(last or 0):
                    continue
                process(eid, ev.get("time") or ev.get("dt"), ev.get("device") or "http", str(ev.get("card_uid") or ev.get("ekey") or ""))
                last = eid
            _save({"last_id": last})
        time.sleep(interval)

def run_file():
    d = _cfg("file_dir", "/var/spool/fitintel-events")
    os.makedirs(d, exist_ok=True)
    done = os.path.join(d, "done")
    os.makedirs(done, exist_ok=True)
    print("МОСТ v4 (file) ЗАПУЩЕН: %s" % d, flush=True)
    while True:
        for path in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                ev = json.load(open(path, encoding="utf-8"))
                process(ev.get("id") or os.path.basename(path), ev.get("time") or "",
                        ev.get("device") or "file", str(ev.get("card_uid") or ev.get("ekey") or ""))
                os.rename(path, os.path.join(done, os.path.basename(path)))
            except Exception as e:
                print("file event error:", str(e)[:100], flush=True)
        time.sleep(2)

for _ in range(20):
    if ensure_token():
        break
    time.sleep(15)
if not JWT:
    raise SystemExit("FitIntel не отвечает (login/refresh)")

if MODE == "fb":
    run_fb()
elif MODE == "http":
    run_http()
elif MODE == "file":
    run_file()
else:
    print("MODE=none: источника СКУД нет — входы через считыватель на стойке. Мост в режиме ожидания.", flush=True)
    while True:
        time.sleep(60)
