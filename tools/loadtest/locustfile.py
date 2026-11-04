"""Locust-нагрузка FitIntel Pro API.
Покрытие: все GET-эндпоинты из OpenAPI (клиенты, визиты, оплаты, аналитика, уведомления,
доступ, тарифы) + сценарии турникета (вход/выход) + создание клиента + доска Kerong.
Запуск (PowerShell, ПК):
    pip install locust
    $env:FI_TOKEN = "<токен с nfs>"
    locust -f tools/loadtest/locustfile.py --host http://192.168.101.182 --headless -u 100 -r 20 -t 10m --csv loadrun
Результаты: loadrun_stats.csv, loadrun_failures.csv рядом с этим файлом.
"""
import os, random, uuid
from locust import HttpUser, task, between, events

TOKEN = os.getenv("FI_TOKEN", "")
HEADERS = {"Authorization": "Bearer " + TOKEN} if TOKEN else {}

GET_PREFIXES = ("/clients", "/visits", "/access", "/payments", "/analytics",
                "/notify", "/tariffs", "/subscriptions", "/trainers", "/schedule", "/reports")
GROUP_W = {"clients": 10, "visits": 9, "access": 7, "payments": 6, "analytics": 5,
           "notify": 4, "tariffs": 2, "default": 1}
REAL_ID = None  # реальный client_id, подставляется в {client_id}/{id}

class FitIntelUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(14)
    def turnstile_entry(self):
        self.client.post("/api/v1/visits/entry", headers=HEADERS,
                         json={"rfid_code": "LT%06d" % random.randint(0, 999999)},
                         name="POST /visits/entry")

    @task(14)
    def turnstile_exit(self):
        self.client.post("/api/v1/visits/exit", headers=HEADERS,
                         json={"rfid_code": "LT%06d" % random.randint(0, 999999)},
                         name="POST /visits/exit")

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
    """Подтягиваем реальные GET-пути из OpenAPI и вешаем задачи с весами."""
    import requests
    global REAL_ID
    try:
        r = requests.get(host + "/api/v1/openapi.json", headers=HEADERS, timeout=10)
        spec = r.json() if r.status_code == 200 else {}
        try:
            rc = requests.get(host + "/api/v1/clients/?page=1&size=1", headers=HEADERS, timeout=10)
            data = rc.json()
            items = data.get("items") or data.get("data") or (data if isinstance(data, list) else [])
            if items:
                REAL_ID = str(items[0].get("id"))
        except Exception:
            pass
    except Exception:
        spec = {}
    for path, ops in (spec.get("paths") or {}).items():
        if "get" not in ops or not any(p in path for p in GET_PREFIXES):
            continue
        g = next((k for k in GROUP_W if k in path), "default")
        w = GROUP_W[g]
        def make(p):
            def t(self):
                url = p
                for seg in p.split("/"):
                    if seg.startswith("{") and seg.endswith("}"):
                        url = url.replace(seg, REAL_ID or str(uuid.uuid4()))
                self.client.get(url, headers=HEADERS, name="GET " + p.split("{")[0] + "{id}")
            return t
        setattr(FitIntelUser, "auto_%s_%d" % (path.strip("/").replace("/", "_").replace("{", "").replace("}", ""),
                                              abs(hash(path)) % 10**6), task(weight=w)(make(path)))

@events.test_start.add_listener
def _on_start(environment, **kwargs):
    _build_get_tasks(environment.host)
