"""FitIntel Pro Desktop API Client"""
import requests
from typing import Optional, Dict, Any, List

class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8001/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def set_token(self, token: str):
        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self):
        self.token = None
        self.session.headers.pop("Authorization", None)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def login(self, username: str, password: str) -> Dict[str, Any]:
        data = {"username": username, "password": password}
        resp = self.session.post(self._url("/auth/token"), data=data)
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
        return resp.json()

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
        return resp.json()

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
        return resp.json()

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
        return resp.json()

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
