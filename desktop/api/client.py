"""FitIntel Pro Desktop API Client"""
import requests
from typing import Optional, Dict, Any, List


class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8001/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.session = requests.Session()

    def set_token(self, token: str):
        self.token = token
        self.session.headers["Authorization"] = "Bearer " + token

    def clear_token(self):
        self.token = None
        self.session.headers.pop("Authorization", None)

    def _url(self, path: str) -> str:
        path = path.lstrip("/")
        return self.base_url + "/" + path

    def _get(self, path: str, params: dict = None) -> Any:
        resp = self.session.get(self._url(path), params=params or {})
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: dict = None, data: dict = None, headers: dict = None) -> Any:
        kwargs = {}
        if json_data is not None:
            kwargs["json"] = json_data
        if data is not None:
            kwargs["data"] = data
        if headers is not None:
            kwargs["headers"] = headers
        resp = self.session.post(self._url(path), **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, json_data: dict = None) -> Any:
        kwargs = {}
        if json_data is not None:
            kwargs["json"] = json_data
        resp = self.session.put(self._url(path), **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> Any:
        resp = self.session.delete(self._url(path))
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        data = {"username": username, "password": password}
        resp = self.session.post(
            self._url("/auth/token"),
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        resp.raise_for_status()
        return resp.json()

    def me(self) -> Dict[str, Any]:
        return self._get("/auth/me")

    def health(self) -> Dict[str, Any]:
        return self._get("/health/")

    def get_clients(self) -> List[Dict[str, Any]]:
        return self._get("/clients/")

    def get_client(self, client_id: str) -> Dict[str, Any]:
        return self._get("/clients/" + client_id)

    def create_client(self, data: dict) -> Dict[str, Any]:
        return self._post("/clients/", json_data=data)

    def update_client(self, client_id: str, data: dict) -> Dict[str, Any]:
        return self._put("/clients/" + client_id, json_data=data)

    def delete_client(self, client_id: str) -> Dict[str, Any]:
        return self._delete("/clients/" + client_id)

    def get_subscriptions(self) -> List[Dict[str, Any]]:
        return self._get("/subscriptions/")

    def get_subscription(self, sub_id: str) -> Dict[str, Any]:
        return self._get("/subscriptions/" + sub_id)

    def create_subscription(self, data: dict) -> Dict[str, Any]:
        return self._post("/subscriptions/", json_data=data)

    def freeze_subscription(self, sub_id: str) -> Dict[str, Any]:
        return self._post("/subscriptions/" + sub_id + "/freeze")

    def unfreeze_subscription(self, sub_id: str) -> Dict[str, Any]:
        return self._post("/subscriptions/" + sub_id + "/unfreeze")

    def get_tariffs(self) -> List[Dict[str, Any]]:
        return self._get("/tariffs/")

    def create_tariff(self, data: dict) -> Dict[str, Any]:
        return self._post("/tariffs/", json_data=data)

    def get_visits(self) -> List[Dict[str, Any]]:
        return self._get("/visits/")

    def get_visit_stats(self) -> Dict[str, Any]:
        return self._get("/visits/stats")

    def entry_visit(self, data: dict) -> Dict[str, Any]:
        return self._post("/visits/entry", json_data=data)

    def exit_visit(self, data: dict) -> Dict[str, Any]:
        return self._post("/visits/exit", json_data=data)

    def check_access(self, data: dict) -> Dict[str, Any]:
        return self._post("/access/check", json_data=data)

    def grant_access(self, data: dict) -> Dict[str, Any]:
        return self._post("/access/grant", json_data=data)

    def get_wallet(self) -> Dict[str, Any]:
        return self._get("/wallet/me")

    def get_balance(self) -> Dict[str, Any]:
        return self._get("/wallet/me/balance")

    def get_transactions(self) -> List[Dict[str, Any]]:
        return self._get("/wallet/me/transactions")

    def deposit(self, data: dict) -> Dict[str, Any]:
        return self._post("/wallet/me/deposit", json_data=data)

    def get_payments(self) -> List[Dict[str, Any]]:
        return self._get("/payments/me")

    def get_cash_desk_status(self) -> Dict[str, Any]:
        return self._get("/cash-desk/status")

    def open_shift(self, data: dict) -> Dict[str, Any]:
        return self._post("/cash-desk/shift/open", json_data=data)

    def close_shift(self, data: dict) -> Dict[str, Any]:
        return self._post("/cash-desk/shift/close", json_data=data)

    def create_sale(self, data: dict) -> Dict[str, Any]:
        return self._post("/cash-desk/sales", json_data=data)

    def get_receipts(self) -> List[Dict[str, Any]]:
        return self._get("/receipts/")

    def verify_face(self, face_encoding: list, terminal_id: str = "desktop-001", location: str = "desk") -> Dict[str, Any]:
        payload = {"face_encoding": face_encoding, "terminal_id": terminal_id, "terminal_location": location}
        return self._post("/face-id/verify", json_data=payload)

    def register_face(self, data: dict) -> Dict[str, Any]:
        return self._post("/face-id/register", json_data=data)

    def get_face_logs(self) -> List[Dict[str, Any]]:
        return self._get("/face-id/logs")

    def verify_license(self, license_key: str, device_id: str) -> Dict[str, Any]:
        payload = {"license_key": license_key, "device_id": device_id}
        return self._post("/license/verify", json_data=payload)

    def get_license_limits(self, license_key: str) -> Dict[str, Any]:
        return self._get("/license/limits", params={"license_key": license_key})

    def get_dashboard(self) -> Dict[str, Any]:
        return self._get("/analytics/dashboard")

    def get_devices(self) -> List[Dict[str, Any]]:
        return self._get("/devices/")

    def get_users(self) -> List[Dict[str, Any]]:
        return self._get("/users/")

    def get_roles(self) -> List[Dict[str, Any]]:
        return self._get("/roles/")

    def get_permissions(self) -> List[Dict[str, Any]]:
        return self._get("/permissions/")

    def create_user(self, data: dict) -> Dict[str, Any]:
        return self._post("/users/", json_data=data)
