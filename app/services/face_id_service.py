import math
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.face_id import FaceTemplate, FaceRecognitionLog
from app.models.subscription import Subscription

MATCH_THRESHOLD = 0.6  # Порог dlib (евклидово расстояние)

class FaceIDService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def distance(a, b) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def find_best_match(self, face_encoding: list) -> Tuple[Optional[FaceTemplate], float]:
        templates = self.db.query(FaceTemplate).filter(FaceTemplate.is_active == True).all()
        best_match, best_dist = None, float('inf')
        for t in templates:
            if not t.face_encoding:
                continue
            d = self.distance(t.face_encoding, face_encoding)
            if d < best_dist:
                best_dist = d
                best_match = t
        confidence = max(0.0, 1.0 - best_dist) if best_match else 0.0
        if best_match and best_dist < MATCH_THRESHOLD:
            return best_match, confidence
        return None, confidence

    def register_face(self, client_id, face_encoding, photo_path=None, quality_score=None):
        existing = self.db.query(FaceTemplate).filter(
            FaceTemplate.client_id == client_id, FaceTemplate.is_active == True
        ).all()
        template = FaceTemplate(
            client_id=client_id, user_id=None, user_type="client",
            face_encoding=face_encoding, photo_path=photo_path,
            quality_score=quality_score, is_active=True, is_primary=(len(existing) == 0)
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def has_active_subscription(self, client_id) -> bool:
        today = datetime.now(timezone.utc).date()
        sub = self.db.query(Subscription).filter(
            Subscription.client_id == client_id,
            Subscription.status == "ACTIVE",
            Subscription.end_date >= today
        ).first()
        return sub is not None

    def log_recognition(self, template_id, terminal_id, status, reason, confidence):
        log = FaceRecognitionLog(
            face_template_id=template_id, user_id=None, user_type="client",
            terminal_id=terminal_id or "unknown", status=status,
            reason=reason, confidence_score=confidence
        )
        self.db.add(log)
        self.db.commit()
