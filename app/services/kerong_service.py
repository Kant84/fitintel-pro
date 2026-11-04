"""Интеграция с Kerong API. Список замков НЕ хранится в БД FitIntel —
он запрашивается у Kerong API в момент необходимости."""
import requests
from typing import List, Dict, Any
from sqlalchemy.orm import Session


class KerongService:
    def __init__(self, db: Session, base_url: str, bu_uuid: str):
        self.db = db
        self.base_url = (base_url or "").rstrip("/")
        self.bu_uuid = bu_uuid

    def open_lock(self, cu_board_id: int, lock_number: int) -> Dict[str, Any]:
        url = f"{self.base_url}/kerong-api/open-lock"
        payload = {"buBoardUuid": self.bu_uuid, "cuBoardId": cu_board_id, "lockNumber": lock_number}
        try:
            r = requests.post(url, json=payload, timeout=3)
            if r.status_code == 201:
                return {"ok": True, "status": "OPENED"}
            try:
                err = r.json()
                msg = err.get("info", {}).get("message") or err.get("detail") or r.text
            except Exception:
                msg = r.text[:200]
            return {"ok": False, "error": f"HTTP {r.status_code}: {msg}"}
        except requests.exceptions.Timeout:
            return {"ok": False, "error": "Таймаут подключения к Kerong API"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def get_locks(self, cu_board_id: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/kerong-api/locks-list"
        params = {"kr-bu-uuid": self.bu_uuid, "kr-cu-id": cu_board_id}
        try:
            r = requests.get(url, params=params, timeout=3)
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def set_unlocking_time(self, cu_board_id: int, ms: int) -> Dict[str, Any]:
        url = f"{self.base_url}/kerong-api/set-unlocking-time"
        payload = {"krBuId": self.bu_uuid, "krCuId": cu_board_id, "unlockingTime": ms}
        try:
            r = requests.post(url, json=payload, timeout=3)
            return {"ok": r.status_code == 200, "status_code": r.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

