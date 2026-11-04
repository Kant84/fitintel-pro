"""Locust-нагрузка FitIntel Pro API (v3 - турникет с учетом занятости клиентов).
Модель: FREE (на улице) -> вход -> OPEN (внутри, client_id -> visit_id) -> выход -> FREE.
Стационарно: внутри одновременно = вход/с x среднее время визита. Отказы только если
все клиенты пула внутри (реалистичное переполнение). Ограничение: время визита ~секунды
(через wait_time пользователя) - для throughput-теста этого достаточно.
"""
import os, random, uuid, threading
from locust import HttpUser, task, between, events

TOKEN = os.getenv("FI_TOKEN", "")
HEADERS = {"Authorization": "Bearer " + TOKEN} if TOKEN else {}

GET_PREFIXES = ("/clients", "/visits", "/access", "/payments", "/analytics",
                "/notify", "/tariffs", "/subscriptions", "/trainers", "/schedule", "/reports")
GROUP_W = {"clients": 10, "visits": 9, "access": 7, "payments": 6, "analytics": 5,
           "notify": 4, "tariffs": 2, "default": 1}

FREE = []          # client_id на улице (доступны для входа)
OPEN = {}          # client_id -> visit_id (внутри)
REAL_ID = None
_lock = threading.Lock()

def _take_free():
    with _lock:
        if not FREE:
            return None
        i = random.randrange(len(FREE))
        cid = FREE[i]
        FREE[i] = FREE[-1]
        FREE.pop()
        return cid

def _return_free(cid):
    with _lock:
        FREE.append(cid)

def _take_open():
    """Случайный (client_id, visit_id) внутри - и сразу освобождает слот."""
    with _lock:
        if not OPEN:
            return None, None
        cid = random.choice(list(OPEN.keys()))
        return cid, OPEN.pop(cid)

class FitIntelUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(14)
    def turnstile_entry(self):
        cid = _take_free()
        if cid:
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
                    if cid and vid:
                        with _lock:
                            OPEN[cid] = vid
                except Exception:
                    pass
            elif cid:
                _return_free(cid)   # отказ (абонемент/уже внутри) - клиент снова на улице
            r.success()

    @task(14)
    def turnstile_exit(self):
        cid, vid = _take_open()
        if not vid:
            vid = str(uuid.uuid4())   # честный 404 на случайном id
        with self.client.post("/api/v1/visits/exit", headers=HEADERS,
                              json={"visit_id": vid},
                              name="POST /visits/exit", catch_response=True) as r:
            r.success()

    @task(8)
    def client_create(self):
        n = random.randint(0, 999999)
        with self.client.post("/api/v1/clients", headers=HEADERS,
                              json={"first_name": "Load", "last_name": "Test",
                                    "phone": "+7999LT%06d" % n, "email": "lt%06d@load.test" % n},
                              name="POST /clients", catch_response=True) as r:
            if r.status_code == 201:
                try:
                    cid = (r.json() or {}).get("id")
                    if cid:
                        _return_free(str(cid))   # новый клиент сразу доступен для входов
                except Exception:
                    pass
            r.success()

    @task(4)
    def kerong_board(self):
        self.client.get("/api/v1/notify/kerong/board", headers=HEADERS,
                        name="GET /notify/kerong/board")

    @task(2)
    def cn_settings(self):
        self.client.get("/api/v1/notify/client-settings", headers=HEADERS,
                        name="GET /notify/client-settings")

def _build_get_tasks(host):
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
    # пул клиентов: до 4 страниц по 500 = до 2000 человек на улице
    for page in range(1, 5):
        got = 0
        for url in ("/api/v1/clients/?page=%d&size=500" % page,
                    "/api/v1/clients/?limit=500&offset=%d" % ((page - 1) * 500)):
            try:
                rc = requests.get(host + url, headers=HEADERS, timeout=15)
                data = rc.json()
                items = data.get("items") or data.get("data") or (data if isinstance(data, list) else [])
                ids = [str(i.get("id")) for i in items if i.get("id")]
                if ids:
                    with _lock:
                        FREE.extend(ids)
                    if REAL_ID is None:
                        REAL_ID = ids[0]
                    got = len(ids)
                    break
            except Exception:
                pass
        if got == 0:
            break
    with _lock:
        print("FREE_CLIENTS:", len(FREE), "OPEN:", len(OPEN))

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
