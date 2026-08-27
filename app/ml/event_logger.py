"""E60: Event Logger — центральный сборщик событий для ML."""
import uuid
import json
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

class EventLogger:
    """Логирует все события системы в ml_events."""
    
    EVENT_TYPES = [
        "ui_click", "api_call", "error", "business_event",
        "prediction", "access_granted", "access_denied", "rfid_write"
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(self,
        event_type: str,
        payload: dict,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source: str = "api"
    ) -> str:
        """Записать событие в ml_events."""
        if event_type not in self.EVENT_TYPES:
            self.EVENT_TYPES.append(event_type)
        
        event_id = str(uuid.uuid4())
        sql = text("""
            INSERT INTO ml_events (id, event_type, payload, client_id, user_id, session_id, source, created_at)
            VALUES (:id, :type, :payload, :client_id, :user_id, :session_id, :source, NOW())
        """)
        self.db.execute(sql, {
            "id": event_id,
            "type": event_type,
            "payload": json.dumps(payload),
            "client_id": client_id,
            "user_id": user_id,
            "session_id": session_id,
            "source": source,
        })
        self.db.commit()
        return event_id
    
    def log_access(self, client_card: str, device_id: str, granted: bool,
                   client_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Логировать проход через СКУД."""
        return self.log(
            event_type="access_granted" if granted else "access_denied",
            payload={"client_card": client_card, "device_id": device_id, "granted": granted},
            client_id=client_id,
            user_id=user_id,
            source="skud",
        )
    
    def log_api(self, endpoint: str, method: str, latency_ms: float,
                status_code: int, user_id: Optional[str] = None) -> str:
        """Логировать API-вызов."""
        return self.log(
            event_type="api_call",
            payload={"endpoint": endpoint, "method": method, "latency_ms": latency_ms, "status": status_code},
            user_id=user_id,
            source="api",
        )
    
    def log_error(self, error_type: str, message: str, traceback: Optional[str] = None,
                  user_id: Optional[str] = None) -> str:
        """Логировать ошибку."""
        return self.log(
            event_type="error",
            payload={"error_type": error_type, "message": message, "traceback": traceback},
            user_id=user_id,
            source="system",
        )
