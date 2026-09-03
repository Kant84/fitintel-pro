import json
import urllib.request
import urllib.error
import os

CACHE_FILE = "rfid_uid_cache.json"


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class RFIDApiOps:
    def __init__(self, tab):
        self.tab = tab
        self._req = tab._req
        self._base = tab._base
        self._token = tab._token
        self._log = tab._log

    def unbind_uid(self, uid):
        """Отвязка UID от клиента. Пробует 5 endpoint'ов."""
        tok = self._token()
        if not tok and hasattr(self.tab, "api") and hasattr(self.tab.api, "token"):
            tok = self.tab.api.token
        if not tok:
            self._log(self.tab.log, "⚠️ Нет токена для отвязки")
            return

        target_cred_id = self._find_credential_id(tok, uid)
        if not target_cred_id:
            self._log(self.tab.log, f"ℹ️ UID {uid} не найден в базе")
            # Удаляем из кэша на всякий случай
            cache = _load_cache()
            if uid.upper() in cache:
                del cache[uid.upper()]
                _save_cache(cache)
            return

        self._log(self.tab.log, f"🔍 Найден credential ID: {target_cred_id}")

        endpoints = [
            (f"/credentials/rfid/{target_cred_id}", "DELETE /rfid/{id}", "DELETE", None),
            (f"/credentials/{target_cred_id}", "DELETE /{id}", "DELETE", None),
            (f"/credentials/rfid/{target_cred_id}", "PATCH client_id=null", "PATCH", {"client_id": None}),
            (f"/credentials/rfid/{target_cred_id}", "PUT client_id=null", "PUT", {"client_id": None}),
            ("/rfid/unbind", "POST /rfid/unbind", "POST", {"credential_id": target_cred_id}),
        ]

        for endpoint, label, method, payload in endpoints:
            try:
                if payload is not None:
                    req = urllib.request.Request(
                        self._base() + endpoint,
                        data=json.dumps(payload).encode(),
                        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
                        method=method)
                else:
                    req = urllib.request.Request(
                        self._base() + endpoint,
                        headers={"Authorization": "Bearer " + tok},
                        method=method)
                urllib.request.urlopen(req, timeout=10)
                self._log(self.tab.log, f"✅ UID {uid} отвязан ({label})")
                # Удаляем из кэша
                cache = _load_cache()
                if uid.upper() in cache:
                    del cache[uid.upper()]
                    _save_cache(cache)
                self._clear_widget()
                return
            except urllib.error.HTTPError as e:
                self._log(self.tab.log, f"⚠️ {label} -> HTTP {e.code}: {e.read().decode()[:120]}")
            except Exception as e:
                self._log(self.tab.log, f"⚠️ {label} -> {e}")

        self._log(self.tab.log, f"⚠️ Все способы отвязки не сработали. Проверьте http://localhost:8001/docs")

    def save_to_cache(self, uid, client_name):
        """Сохраняет UID → имя клиента в локальный кэш."""
        cache = _load_cache()
        cache[uid.upper()] = client_name
        _save_cache(cache)
        self._log(self.tab.log, f"💾 UID {uid} сохранён в кэш: {client_name}")

    def _find_credential_id(self, tok, uid):
        try:
            clients = self._req("GET", "/clients/?limit=200")
            if isinstance(clients, dict) and "_err" in clients:
                return None
            for c in clients.get("items", []):
                cid = c.get("id")
                creds = self._req("GET", f"/credentials/rfid/client/{cid}")
                creds_list = creds if isinstance(creds, list) else creds.get("credentials", creds.get("items", []))
                for cred in creds_list:
                    c_uid = cred.get("credential_value") or cred.get("uid") or cred.get("rfid_uid")
                    if c_uid and str(c_uid).upper() == str(uid).upper():
                        return cred.get("id")
        except Exception:
            pass
        return None

    def _clear_widget(self):
        try:
            import rfid_monitor_widget as rw
            import gc
            for obj in gc.get_objects():
                if isinstance(obj, rw.RFIDMonitorWidget):
                    obj.clear_client()
                    break
        except Exception:
            pass