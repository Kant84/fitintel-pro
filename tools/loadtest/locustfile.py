"""Locust-нагрузка FitIntel Pro API (v2 - реальные сценарии турникета по схемам VisitEntryRequest/VisitExitRequest).
Запуск (PowerShell, ПК):
    $env:FI_TOKEN = "<токен с nfs>"
    locust -f tools/loadtest/locustfile.py --host http://192.168.101.182 --headless -u 100 -r 20 -t 10m --csv loadrun
"""
import os, random, uuid, threading
from locust import HttpUser, task, between, events

TOKEN = os.getenv("FI_TOKEN", "")
HEADERS = {"Authorization": "Bearer " + TOKEN} if TOKEN else {}

GET_PREFIXES = ("/clients", "/visits", "/access", "/payments", "/analytics",
                "/notify", "/tariffs", "/subscriptions", "/trainers", "/schedule", "/reports")
GROUP_W = {"clients": 10, "visits": 9, "access": 7, "payments": 6, "analytics": 5,
           "notify": 4, "tariffs": 2, "default": 1}

REAL_ID = None          # первый клиент (для GET {client_id})
CLIENT_POOL = []        # пул реальных client_id для входов
VISIT_POOL = []         # пул visit_id от успешных входов (для выходов)
_lock = threading.Lock()

def _remember(seq, item, cap=500):
    with _lock:
        seq.append(item)
        if len(seq) > cap:
            del seq[:-cap]

def _pick(seq):
    with _lock:
        return random.choice(seq) if seq else None

class FitIntelUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(14)
    def turnstile_entry(self):
        cid = _pick(CLIENT_POOL)
        if cid and random.random() < 0.7:
            payload = {"client_id": cid, "access_method": "CARD",
                       "access_device_id": "LOADTEST-T1", "zone": "GYM"}
        else:
            payload = {"card_id": "LT%06d" % random.randint(0, 999999),
                       "access_method": "CARD", "access_device_id": "LOADTEST-T1"}
        with self.client.post("/api/v1/visits/entry", headers=HEADERS, json=payload,
                              name="POST /visits/entry", catch_response=True) as r:
            if r.status_code == 201:
                try:
                    vid = (r.json() or {}).get("id")
                    if vid:
                        _remember(VISIT_POOL, vid)
                except Exception:
                    pass
            r.success()

    @task(14)
    def turnstile_exit(self):
        vid = _pick(VISIT_POOL) or str(uuid.uuid4())
        self.client.post("/api/v1/visits/exit", headers=HEADERS,
                         json={"visit_id": vid}, name="POST /visits/exit")

    @task(8)
    def client_create(self):
        n = random.randint(0, 999999)
        self.client.post("/api/v1/clients", headers=HEADERS,
                         json={"first_name": "Load", "last_name": "Test",
                               "phone": "+7999LT%06d" % n, "email": "lt%06d@load.test" % n},
                         name="POST /clients")

    @task(4)
    def kerong_board(self):
        self.client.get("/api/v1/notify/kerong/board", headers=HEADERS,
                        name="GET /notify/kerong/board")

    @task(2)
    def cn_settings(self):
        self.client.get("/api/v1/notify/client-settings", headers=HEADERS,
                        name="GET /notify/client-settings")

def _build_get_tasks(host):
    """OpenAPI (оба возможных пути) + пул реальных client_id."""
    import requests
    global REAL_ID
    spec = {}
    for pth in ("/api/v1/openapi.json", "/openapi.json"):
        try:
            r = requests.get(host + pth, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                spec = r.json()
                print("OPENAPI_OK:", pth)
                break
        except Exception:
            pass
    # пул клиентов (до 500 шт) + REAL_ID
    for url in ("/api/v1/clients/?limit=500", "/api/v1/clients/?page=1&size=500"):
        try:
            rc = requests.get(host + url, headers=HEADERS, timeout=15)
            data = rc.json()
            items = data.get("items") or data.get("data") or (data if isinstance(data, list) else [])
            if items:
                ids = [str(i.get("id")) for i in items if i.get("id")]
                if ids:
                    CLIENT_POOL.extend(ids)
                    REAL_ID = ids[0]
                    print("CLIENT_POOL:", len(ids))
                    break
        except Exception:
            pass
    for path, ops in (spec.get("paths") or {}).items():
        if "get" not in ops or not any(p in path for p in GET_PREFIXES):
            continue
        g = next((k for k in GROUP_W if k in path), "default")
        def make(p):
            def t(self):
                url = p
                for seg in p.split("/"):
                    if seg.startswith("{") and seg.endswith("}"):
                        url = url.replace(seg, REAL_ID or str(uuid.uuid4()))
                self.client.get(url, headers=HEADERS, name="GET " + p.split("{")[0] + "{id}")
            return t
        setattr(FitIntelUser, "auto_%s_%d" % (path.strip("/").replace("/", "_").replace("{", "").replace("}", ""),
                                              abs(hash(path)) % 10**6), task(weight=GROUP_W[g])(make(path)))

@events.test_start.add_listener
def _on_start(environment, **kwargs):
    _build_get_tasks(environment.host)
