"""FitIntel Pro Desktop API Client"""
import requests
from typing import Optional, Dict, Any, List

class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8001/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        try:
            from app_logging import log as _log
            def _resp_hook(resp, *args, **kwargs):
                if resp.status_code >= 400:
                    _log.warning("%s %s -> %s: %s", resp.request.method, resp.url,
                                 resp.status_code, resp.text[:200])
            self.session.hooks["response"].append(_resp_hook)
        except Exception:
            pass

    def set_token(self, token: str):
        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self):
        self.token = None
        self.session.headers.pop("Authorization", None)

    @staticmethod
    def _as_list(data) -> List[Dict[str, Any]]:
        """API может вернуть list или dict с вложенным списком."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ("items", "data", "results", "visits", "clients",
                      "subscriptions", "logs", "records", "entries", "users",
                      "devices", "drivers"):
                if isinstance(data.get(k), list):
                    return data[k]
        return []

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def login(self, username: str, password: str) -> Dict[str, Any]:
        payload = {"login": username, "password": password}
        resp = self.session.post(self._url("/auth/login"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def me(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/auth/me"))
        resp.raise_for_status()
        return resp.json()

    def health(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/health/"))
        resp.raise_for_status()
        return resp.json()

    # --- Clients ---
    def get_clients(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/clients/"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    def create_client(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(self._url("/clients/"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def update_client(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.patch(self._url(f"/clients/{client_id}"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete_client(self, client_id: str):
        resp = self.session.delete(self._url(f"/clients/{client_id}"))
        resp.raise_for_status()

    # --- Subscriptions ---
    def get_subscriptions(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/subscriptions/"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    def create_subscription(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(self._url("/subscriptions/"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def freeze_subscription(self, sub_id: str) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/subscriptions/{sub_id}/freeze"))
        resp.raise_for_status()
        return resp.json()

    def unfreeze_subscription(self, sub_id: str) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/subscriptions/{sub_id}/unfreeze"))
        resp.raise_for_status()
        return resp.json()

    # --- Visits ---
    def get_visits(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/visits/"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    def get_visit_stats(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/visits/stats"))
        resp.raise_for_status()
        return resp.json()

    # --- Face ID ---
    def register_face(self, user_id: str, user_type: str, face_encoding: List[float], 
                      photo_path: str = "", quality_score: float = 0.0) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "user_type": user_type,
            "face_encoding": face_encoding,
            "photo_path": photo_path,
            "quality_score": quality_score
        }
        resp = self.session.post(self._url("/face-id/register"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def verify_face(self, face_encoding: List[float], terminal_id: str = "desktop-001",
                    location: str = "Ресепшен") -> Dict[str, Any]:
        payload = {
            "face_encoding": face_encoding,
            "terminal_id": terminal_id,
            "terminal_location": location
        }
        resp = self.session.post(self._url("/face-id/verify"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_face_logs(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/face-id/logs"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    # --- License ---
    def verify_license(self, license_key: str, device_id: str) -> Dict[str, Any]:
        payload = {"license_key": license_key, "device_id": device_id}
        resp = self.session.post(self._url("/license/verify"), json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_license_limits(self, license_key: str) -> Dict[str, Any]:
        resp = self.session.get(self._url("/license/limits"), params={"license_key": license_key})
        resp.raise_for_status()
        return resp.json()

    # --- Analytics ---
    def get_dashboard(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/dashboard"))
        resp.raise_for_status()
        return resp.json()

    # --- Dashboard / AI Analytics ---
    def get_churn(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/ai/churn"))
        resp.raise_for_status()
        return resp.json()

    def get_risk_segments(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/ai/risk-segments"))
        resp.raise_for_status()
        return resp.json()

    # --- Users ---
    def get_users(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/users/"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    # --- Devices (DAL) ---
    def get_devices(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/dal/devices"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    def get_drivers(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/dal/drivers"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    # --- Payments / Accounting ---
    def get_accounting_entries(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/accounting/entries"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    def get_sales_report(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/sales/report"))
        resp.raise_for_status()
        return resp.json()

    # --- UI-Config (E51) ---
    def get_ui_my(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/ui-config/my"))
        resp.raise_for_status()
        return resp.json()

    def get_ui_screens(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/ui-config/screens"))
        resp.raise_for_status()
        return resp.json().get("screens", [])

    def get_ui_roles(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/ui-config/roles"))
        resp.raise_for_status()
        return resp.json()

    def set_ui_role_screens(self, role: str, screens: List[str]) -> Dict[str, Any]:
        resp = self.session.put(self._url(f"/ui-config/roles/{role}/screens"),
                                json={"screens": screens})
        resp.raise_for_status()
        return resp.json()

    def reset_ui_role(self, role: str) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/ui-config/roles/{role}/reset"))
        resp.raise_for_status()
        return resp.json()

# ============================ E55_EXT ============================
import requests as _rq

def _e55_url(self, path):
    base = (getattr(self, "base_url", None) or getattr(self, "base", None)
            or getattr(self, "BASE_URL", None) or "http://localhost:8001")
    return str(base).rstrip("/") + "/api/v1" + path

def _e55_sess(self):
    return getattr(self, "session", None) or getattr(self, "_session", None) or _rq

def _e55_get(self, path, params=None):
    r = _e55_sess(self).get(_e55_url(self, path), params=params or {})
    r.raise_for_status()
    try: return r.json()
    except Exception: return r.text

def _e55_post(self, path, payload=None, files=None, data=None):
    s = _e55_sess(self)
    if files is not None:
        r = s.post(_e55_url(self, path), files=files, data=data or {})
    else:
        r = s.post(_e55_url(self, path), json=payload or {})
    r.raise_for_status()
    try: return r.json()
    except Exception: return r.text

def _e55_list(self, data):
    f = getattr(self, "_as_list", None)
    if f:
        try: return f(data)
        except Exception: pass
    if isinstance(data, dict):
        for k in ("items","data","results","records","payments","entries"):
            if isinstance(data.get(k), list): return data[k]
        return []
    return data if isinstance(data, list) else []

def verify_face(self, photo_b64, device_id=None):
    p = {"photo": photo_b64}
    if device_id: p["device_id"] = device_id
    return _e55_post(self, "/face-id/verify", p)

def face_engine_info(self): return _e55_get(self, "/face-id/engine/info")
def face_templates(self): return _e55_list(self, _e55_get(self, "/face-id"))
def face_register(self, client_id, photo_b64):
    return _e55_post(self, "/face-id/register", {"client_id": client_id, "photo": photo_b64})

def get_client_payments(self, client_id, status=None, limit=200):
    pr = {"limit": limit}
    if status: pr["status"] = status
    return _e55_list(self, _e55_get(self, "/payments/client/%s" % client_id, pr))

def create_payment(self, amount, payment_method, client_id=None, notes=None,
                   direction=None, category=None):
    p = {"amount": float(amount), "payment_method": payment_method}
    if client_id: p["client_id"] = str(client_id)
    if notes: p["notes"] = notes
    if direction: p["payment_direction"] = direction
    if category: p["payment_category"] = category
    return _e55_post(self, "/payments/", p)

def complete_payment(self, pid): return _e55_post(self, "/payments/%s/complete" % pid)

def refund_payment(self, pid, reason, amount=None, to_balance=False):
    p = {"reason": reason, "refund_to_balance": bool(to_balance)}
    if amount: p["amount"] = float(amount)
    return _e55_post(self, "/payments/%s/refund" % pid, p)

def export_payments(self, date_from=None, date_to=None, client_id=None, fmt="csv"):
    p = {"format": fmt}
    if date_from: p["date_from"] = date_from
    if date_to: p["date_to"] = date_to
    if client_id: p["client_id"] = str(client_id)
    return _e55_post(self, "/reports/payments/export", p)

def download_document(self, document_id, fmt=None):
    pr = {"format": fmt} if fmt else {}
    r = _e55_sess(self).get(_e55_url(self, "/documents/%s/download" % document_id), params=pr)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "")

def issue_card(self, client_id, card_number, valid_until=None, notes=None):
    p = {"client_id": str(client_id), "card_number": str(card_number)}
    if valid_until: p["valid_until"] = valid_until
    if notes: p["notes"] = notes
    return _e55_post(self, "/credentials/card", p)

def issue_bracelet(self, client_id, bracelet_id, valid_until=None):
    p = {"client_id": str(client_id), "bracelet_id": str(bracelet_id)}
    if valid_until: p["valid_until"] = valid_until
    return _e55_post(self, "/credentials/bracelet", p)

def get_client_credentials(self, client_id):
    return _e55_list(self, _e55_get(self, "/credentials/rfid/client/%s" % client_id))

def block_credential(self, cid, reason):
    return _e55_post(self, "/credentials/%s/block" % cid, {"reason": reason})
def unblock_credential(self, cid):
    return _e55_post(self, "/credentials/%s/unblock" % cid)

def get_lockers(self): return _e55_list(self, _e55_get(self, "/lockers"))
def assign_locker(self, lid, client_id, credential_id=None):
    p = {"client_id": str(client_id)}
    if credential_id: p["credential_id"] = str(credential_id)
    return _e55_post(self, "/lockers/%s/assign" % lid, p)
def open_locker(self, lid): return _e55_post(self, "/lockers/%s/open" % lid)
def release_locker(self, lid): return _e55_post(self, "/lockers/%s/release" % lid)
def block_locker(self, lid, reason):
    return _e55_post(self, "/lockers/%s/block" % lid, {"reason": reason})

_NAMES = ["verify_face","face_engine_info","face_templates","face_register",
          "get_client_payments","create_payment","complete_payment","refund_payment",
          "export_payments","download_document","issue_card","issue_bracelet",
          "get_client_credentials","block_credential","unblock_credential",
          "get_lockers","assign_locker","open_locker","release_locker","block_locker"]
_g = globals()
for _n in _NAMES:
    setattr(ApiClient, _n, _g[_n])
# ========================== E55_EXT END ==========================

# ============================ E56_EXT ============================
def _e56_put(self, path, payload=None):
    r = _e55_sess(self).put(_e55_url(self, path), json=payload or {})
    r.raise_for_status()
    try: return r.json()
    except Exception: return r.text

def get_integration_schema(self): return _e55_get(self, "/integrations-config/schema")
def get_integrations(self): return _e55_get(self, "/integrations-config/")
def save_integration(self, service, config):
    return _e56_put(self, "/integrations-config/%s" % service, {"config": config})
def test_integration(self, service):
    return _e55_post(self, "/integrations-config/%s/test" % service)

def get_chats(self): return _e55_list(self, _e55_get(self, "/messenger/chats"))
def get_chat_messages(self, chat_id):
    return _e55_list(self, _e55_get(self, "/messenger/chats/%s/messages" % chat_id))
def send_chat_message(self, chat_id, text):
    return _e55_post(self, "/messenger/chats/%s/send" % chat_id, {"text": text})
def sync_max(self): return _e55_post(self, "/messenger/max/sync")
def demo_chat(self): return _e55_post(self, "/messenger/demo")

_N56 = ["get_integration_schema","get_integrations","save_integration","test_integration",
        "get_chats","get_chat_messages","send_chat_message","sync_max","demo_chat"]
_g56 = globals()
for _n in _N56:
    setattr(ApiClient, _n, _g56[_n])
# ========================== E56_EXT END ==========================

# ============================ E57_EXT ============================
def get_bindings(self): return _e55_list(self, _e55_get(self, "/messenger/bindings"))
def bind_client(self, client_id, max_user_id, client_name=None, role="client"):
    return _e55_post(self, "/messenger/bindings",
                     {"client_id": str(client_id), "max_user_id": str(max_user_id),
                      "client_name": client_name, "role": role})
def notify_client(self, client_id, text, kind="info"):
    return _e55_post(self, "/messenger/notify",
                     {"client_id": str(client_id), "text": text, "kind": kind})
def broadcast(self, audience, text, kind="promo", client_ids=None):
    return _e55_post(self, "/messenger/broadcast",
                     {"audience": audience, "text": text, "kind": kind,
                      "client_ids": client_ids})
def run_reminders(self): return _e55_post(self, "/messenger/reminders/run")
def get_notifications(self, status=None):
    pr = {"status": status} if status else {}
    return _e55_list(self, _e55_get(self, "/messenger/notifications", pr))
def dispatch_notifications(self):
    return _e55_post(self, "/messenger/notifications/dispatch")

_N57 = ["get_bindings","bind_client","notify_client","broadcast","run_reminders",
        "get_notifications","dispatch_notifications"]
_g57 = globals()
for _n in _N57:
    setattr(ApiClient, _n, _g57[_n])
# ========================== E57_EXT END ==========================

# ============================ E58_EXT ============================
def get_notif_settings(self): return _e55_get(self, "/messenger/settings")
def save_notif_settings(self, cfg): return _e56_put(self, "/messenger/settings", cfg)

_g58 = globals()
for _n in ["get_notif_settings", "save_notif_settings"]:
    setattr(ApiClient, _n, _g58[_n])
# ========================== E58_EXT END ==========================
