"""FitIntel Pro Desktop API Client"""
import requests
from typing import Optional, Dict, Any, List


def _rs(resp):
    """raise_for_status с человекочитаемым detail от сервера."""
    try:
        _rs(resp)
    except Exception:
        try:
            d = resp.json().get("detail")
            if d:
                raise RuntimeError(str(d))
        except RuntimeError:
            raise
        except Exception:
            pass
        raise





def _check(resp):
    """HTTP-ошибка -> человеческий текст из detail сервера."""
    if resp.status_code >= 400:
        msg = "Ошибка сервера (код %s)" % resp.status_code
        try:
            d = resp.json()
            det = d.get("detail") if isinstance(d, dict) else None
            if det:
                msg = str(det)
        except Exception:
            pass
        raise RuntimeError(msg)

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

        # Таймаут по умолчанию (10 сек) для ВСЕХ запросов сессии.
        _orig_request = self.session.request
        def _request_with_timeout(method, url, **kwargs):
            kwargs.setdefault("timeout", 10)
            return _orig_request(method, url, **kwargs)
        self.session.request = _request_with_timeout

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
        _check(resp)
        data = resp.json()
        # сохраняем refresh_token сразу (E70 будет обновлять сессию молча)
        rt = data.get("refresh_token")
        if rt:
            self._refresh_token = rt
            _e70_save_tokens(getattr(self, "token", None), rt)
        return data

    def me(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/auth/me"))
        _check(resp)
        return resp.json()

    def health(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/health/"))
        _check(resp)
        return resp.json()

    # --- Clients ---
    def get_clients(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/clients/"))
        _check(resp)
        return self._as_list(resp.json())

    def create_client(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(self._url("/clients/"), json=payload)
        _check(resp)
        return resp.json()

    def update_client(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.patch(self._url(f"/clients/{client_id}"), json=payload)
        _check(resp)
        return resp.json()

    def delete_client(self, client_id: str):
        resp = self.session.delete(self._url(f"/clients/{client_id}"))
        _check(resp)

    # --- Subscriptions ---
    def get_subscriptions(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/subscriptions/"))
        _check(resp)
        return self._as_list(resp.json())

    def create_subscription(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(self._url("/subscriptions/"), json=payload)
        _check(resp)
        return resp.json()

    def freeze_subscription(self, sub_id: str) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/subscriptions/{sub_id}/freeze"))
        _check(resp)
        return resp.json()

    def unfreeze_subscription(self, sub_id: str) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/subscriptions/{sub_id}/unfreeze"))
        _check(resp)
        return resp.json()

    # --- Visits ---
    def get_visits(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/visits/"))
        _check(resp)
        return self._as_list(resp.json())

    def get_visit_stats(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/visits/stats"))
        _check(resp)
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
        _check(resp)
        return resp.json()

    def verify_face(self, face_encoding: List[float], terminal_id: str = "desktop-001",
                    location: str = "Ресепшен") -> Dict[str, Any]:
        payload = {
            "face_encoding": face_encoding,
            "terminal_id": terminal_id,
            "terminal_location": location
        }
        resp = self.session.post(self._url("/face-id/verify"), json=payload)
        _check(resp)
        return resp.json()

    def get_face_logs(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/face-id/logs"))
        _check(resp)
        return self._as_list(resp.json())

    # --- License ---
    def verify_license(self, license_key: str, device_id: str) -> Dict[str, Any]:
        payload = {"license_key": license_key, "device_id": device_id}
        resp = self.session.post(self._url("/license/verify"), json=payload)
        _check(resp)
        return resp.json()

    def get_license_limits(self, license_key: str) -> Dict[str, Any]:
        resp = self.session.get(self._url("/license/limits"), params={"license_key": license_key})
        _check(resp)
        return resp.json()

    # --- Analytics ---
    def get_dashboard(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/dashboard"))
        _check(resp)
        return resp.json()

    # --- Dashboard / AI Analytics ---
    def get_churn(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/ai/churn"))
        _check(resp)
        return resp.json()

    def get_risk_segments(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/ai/risk-segments"))
        _check(resp)
        return resp.json()

    # --- Users ---
    def get_users(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/users/"))
        _check(resp)
        return self._as_list(resp.json())

    # --- Devices (DAL) ---
    def get_devices(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/dal/devices"))
        _check(resp)
        return self._as_list(resp.json())

    def get_drivers(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/dal/drivers"))
        _check(resp)
        return self._as_list(resp.json())

    # --- Payments / Accounting ---
    def get_accounting_entries(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/accounting/entries"))
        _check(resp)
        return self._as_list(resp.json())

    def get_sales_report(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/sales/report"))
        _check(resp)
        return resp.json()

    # --- UI-Config (E51) ---
    def get_ui_my(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/ui-config/my"))
        _check(resp)
        return resp.json()

    def get_ui_screens(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/ui-config/screens"))
        _check(resp)
        return resp.json().get("screens", [])

    def get_ui_roles(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/ui-config/roles"))
        _check(resp)
        return resp.json()

    def set_ui_role_screens(self, role: str, screens: List[str]) -> Dict[str, Any]:
        resp = self.session.put(self._url(f"/ui-config/roles/{role}/screens"),
                                json={"screens": screens})
        _check(resp)
        return resp.json()

    def reset_ui_role(self, role: str) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/ui-config/roles/{role}/reset"))
        _check(resp)
        return resp.json()

# ============================ E55_EXT ============================
import requests as _rq

def _e55_url(self, path):
    base = (getattr(self, "base_url", None) or getattr(self, "base", None)
            or getattr(self, "BASE_URL", None) or "http://localhost:8001")
    base = str(base).rstrip("/")
    if base.endswith("/api/v1"):
        return base + path
    return base + "/api/v1" + path

def _e55_sess(self):
    return getattr(self, "session", None) or getattr(self, "_session", None) or _rq

def _e55_get(self, path, params=None):
    r = _e55_sess(self).get(_e55_url(self, path), params=params or {}, timeout=60)
    _rs(r)
    try: return r.json()
    except Exception: return r.text

def _e55_post(self, path, payload=None, files=None, data=None):
    s = _e55_sess(self)
    if files is not None:
        r = s.post(_e55_url(self, path), files=files, data=data or {}, timeout=180)
    else:
        r = s.post(_e55_url(self, path), json=payload or {}, timeout=180)
    _rs(r)
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
    _rs(r)
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
for _n in ["_e55_get", "_e55_post", "_e55_url", "_e55_sess", "_e55_list"]:
    setattr(ApiClient, _n, _g[_n])   
# ========================== E55_EXT END ==========================

# ============================ E56_EXT ============================
def _e56_put(self, path, payload=None):
    r = _e55_sess(self).put(_e55_url(self, path), json=payload or {})
    _rs(r)
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

# ============================ E59_EXT ============================
def _e55_del(self, path):
    r = _e55_sess(self).delete(_e55_url(self, path))
    _rs(r)
    try: return r.json()
    except Exception: return r.text

def _e55_try(self, kind, paths, payload=None):
    last = None
    for pth in paths:
        try:
            if kind == "get": return _e55_get(self, pth)
            if kind == "post": return _e55_post(self, pth, payload)
        except Exception as e:
            last = e
    raise last

_TARIFF_PATHS = ["/tariffs/", "/tariffs", "/subscriptions/tariffs/", "/subscriptions/tariffs"]

def get_tariffs(self):
    return _e55_list(self, _e55_try(self, "get", _TARIFF_PATHS))

def create_tariff(self, code, name, price, duration_days):
    return _e55_try(self, "post", _TARIFF_PATHS,
                    {"code": code, "name": name, "price": float(price),
                     "duration_days": int(duration_days)})

def update_tariff(self, tid, data):
    return _e56_put(self, "/tariffs/%s" % tid, data)

def delete_tariff(self, tid):
    return _e55_del(self, "/tariffs/%s" % tid)

def delete_user(self, uid):
    return _e55_del(self, "/users/%s" % uid)

def get_documents(self, client_id=None):
    pr = {"client_id": str(client_id)} if client_id else {}
    return _e55_list(self, _e55_get(self, "/documents", pr))

def create_document(self, doc_type, client_id, data=None, template_id=None):
    p = {"type": doc_type, "client_id": str(client_id)}
    if template_id: p["template_id"] = str(template_id)
    if data: p["data"] = data
    return _e55_post(self, "/documents", p)

def delete_document(self, did):
    return _e55_del(self, "/documents/%s" % did)

_N59 = ["get_tariffs","create_tariff","update_tariff","delete_tariff","delete_user",
        "get_documents","create_document","delete_document"]
_g59 = globals()
for _n in _N59:
    setattr(ApiClient, _n, _g59[_n])
# ========================== E59_EXT END ==========================


# === E59B_EXT: PATCH helper + fix update_tariff ===
def _e55_patch(self, path, payload=None):
    import requests
    url = _e55_url(self, path)
    if hasattr(self, "_session"):
        r = self._session.patch(url, json=payload or {}, timeout=30)
    else:
        r = requests.patch(url, json=payload or {}, timeout=30)
    _rs(r)
    try:
        return r.json()
    except Exception:
        return {}

def update_tariff(self, tariff_id, data):
    """Backend accepts PATCH (not PUT) on /tariffs/{id}."""
    last = None
    for base in _TARIFF_PATHS:
        try:
            return _e55_patch(self, base.rstrip("/") + "/" + str(tariff_id), data)
        except Exception as e:
            last = e
    raise last

# ============================ E70_EXT: прозрачное обновление сессии ============================
"""
Схема: access-токен короткий (30 мин). Любой запрос с 401 -> один молчаливый
refresh (refresh_token из client_settings.json, ротация на сервере) -> повтор
исходного запроса. Пользователь не видит «Токен истёк». Если refresh мёртв —
fallback на логин/пароль (если сохранены), иначе 401 доходит до UI (разлогин).
"""
import json as _e70_json
from pathlib import Path as _e70_Path


def _e70_settings_path():
    try:
        from paths import SETTINGS as _p
        return _p
    except Exception:
        return _e70_Path(__file__).resolve().parents[1] / "client_settings.json"


def _e70_load_settings() -> dict:
    try:
        p = _e70_settings_path()
        if p.exists():
            return _e70_json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _e70_save_tokens(token, refresh_token):
    try:
        p = _e70_settings_path()
        cfg = _e70_load_settings()
        if token:
            cfg["token"] = token
            cfg["access_token"] = token
        if refresh_token:
            cfg["refresh_token"] = refresh_token
        p.write_text(_e70_json.dumps(cfg, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    except Exception:
        pass


def _e70_refresh(self) -> bool:
    """Обмен refresh_token на новую пару. Молча, с сохранением в настройки."""
    rt = getattr(self, "_refresh_token", None) or _e70_load_settings().get("refresh_token")
    if not rt:
        return False
    try:
        r = self.session.post(self._url("/auth/refresh"),
                              json={"refresh_token": rt}, timeout=15)
        if r.status_code != 200:
            return False
        data = r.json()
        token = data.get("access_token")
        new_rt = data.get("refresh_token") or rt
        if not token:
            return False
        self._refresh_token = new_rt
        self.set_token(token)
        _e70_save_tokens(token, new_rt)
        try:
            from app_logging import log as _l
            _l.info("E70: сессия обновлена через refresh_token")
        except Exception:
            pass
        return True
    except Exception:
        return False


def _e70_relogin(self) -> bool:
    """Молчаливая повторная авторизация: сначала refresh, потом логин/пароль."""
    if getattr(self, "_e70_refreshing", False):
        return False
    self._e70_refreshing = True
    try:
        if _e70_refresh(self):
            return True

        cfg = _e70_load_settings()
        login = cfg.get("saved_login") or cfg.get("login") or cfg.get("username")
        password = cfg.get("saved_password") or cfg.get("password")
        if not login or not password:
            return False
        old_auth = self.session.headers.pop("Authorization", None)
        try:
            r = self.session.post(self._url("/auth/login"),
                                  json={"login": login, "password": password})
            if r.status_code != 200:
                return False
            data = r.json()
            token = data.get("access_token")
            rt = data.get("refresh_token")
        finally:
            if old_auth and "Authorization" not in self.session.headers:
                self.session.headers["Authorization"] = old_auth
        if not token:
            return False
        if rt:
            self._refresh_token = rt
        self.set_token(token)
        _e70_save_tokens(token, rt)
        try:
            from app_logging import log as _l
            _l.info("E70: сессия обновлена через логин/пароль")
        except Exception:
            pass
        return True
    except Exception:
        return False
    finally:
        self._e70_refreshing = False


_e70_orig_init = ApiClient.__init__

def _e70_init(self, base_url="http://localhost:8001/api/v1"):
    _e70_orig_init(self, base_url)
    self._e70_refreshing = False
    self._refresh_token = _e70_load_settings().get("refresh_token")
    _inner = self.session.request

    def _e70_request(method, url, **kwargs):
        resp = _inner(method, url, **kwargs)
        if resp.status_code == 401 and _e70_relogin(self):
            h = kwargs.get("headers")
            if isinstance(h, dict) and "Authorization" in h:
                h = dict(h)
                h["Authorization"] = "Bearer " + str(getattr(self, "token", "") or "")
                kwargs = dict(kwargs, headers=h)
            resp = _inner(method, url, **kwargs)
        return resp

    self.session.request = _e70_request


ApiClient.__init__ = _e70_init
# ========================== E70_EXT END ==========================

# ============================ E71_EXT ============================
def get_bot_config(self):
    return _e55_get(self, "/max-bot/config")

def save_bot_config(self, body):
    return _e55_post(self, "/max-bot/config", body)

_g71 = globals()
for _n in ["get_bot_config", "save_bot_config"]:
    setattr(ApiClient, _n, _g71[_n])
# ========================== E71_EXT END ==========================

def get_feedbacks(self):
    return _e55_get(self, "/miniapp/feedback")

setattr(ApiClient, "get_feedbacks", get_feedbacks)

def mark_chat_read(self, chat_id):
    return _e55_post(self, "/messenger/chats/%s/read" % chat_id, {})

setattr(ApiClient, "mark_chat_read", mark_chat_read)

# ============================ E72_EXT ============================
def set_club_param(self, key, value):
    resp = self.session.put(self._url("/club-params/" + str(key)), json={"value": str(value)})
    _check(resp)
    return resp.json()

def get_club_params(self):
    resp = self.session.get(self._url("/club-params"))
    _check(resp)
    return resp.json()

_g72 = globals()
for _n in ["set_club_param", "get_club_params"]:
    setattr(ApiClient, _n, _g72[_n])
# ========================== E72_EXT END ==========================

def get_bonus_rules(self):
    return _e55_get(self, "/bonus-rules")

def create_bonus_rule(self, body):
    return _e55_post(self, "/bonus-rules", body)

def delete_bonus_rule(self, rid):
    resp = self.session.delete(self._url("/bonus-rules/" + str(rid)))
    _check(resp)
    return resp.json()

setattr(ApiClient, "get_bonus_rules", get_bonus_rules)
setattr(ApiClient, "create_bonus_rule", create_bonus_rule)
setattr(ApiClient, "delete_bonus_rule", delete_bonus_rule)

def publish_news(self, body):
    return _e55_post(self, "/miniapp/news", body)

setattr(ApiClient, "publish_news", publish_news)
