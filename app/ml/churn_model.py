"""E60: Churn Prediction Model — предсказание оттока клиентов."""
import os
import pickle
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.ml.feature_store import FeatureStore

MODEL_PATH = "models/churn_v1.pkl"

class ChurnModel:
    """
    Модель предсказания оттока клиентов.
    Phase 1: Rule-based (fallback при отсутствии данных для обучения)
    Phase 2: XGBoost (после накопления 100+ размеченных примеров)
    """
    
    RISK_THRESHOLDS = {
        "low": 0.0,
        "medium": 0.4,
        "high": 0.7,
        "critical": 0.9,
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.feature_store = FeatureStore(db)
        self.ml_model = None
        self.version = 1
        self._load_model()
    
    def _load_model(self):
        """Загрузить обученную модель, если есть."""
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                self.ml_model = pickle.load(f)
                self.version += 1
    
    def predict(self, client_id: str) -> Dict[str, any]:
        """
        Предсказать вероятность оттока клиента.
        Returns: {"probability": float, "risk_level": str, "features": dict}
        """
        features = self.feature_store.get_client_features(client_id)
        
        # Если есть ML-модель — используем её
        if self.ml_model:
            vector = self.feature_store.get_churn_features(client_id)
            probability = float(self.ml_model.predict_proba([vector])[0][1])
        else:
            # Rule-based fallback
            probability = self._rule_based_score(features)
        
        risk_level = self._get_risk_level(probability)
        
        return {
            "probability": round(probability, 3),
            "risk_level": risk_level,
            "features": features,
            "model_version": self.version,
            "model_type": "xgboost" if self.ml_model else "rule_based",
        }
    
    def _rule_based_score(self, features: Dict[str, any]) -> float:
        """Rule-based оценка оттока (0.0–1.0)."""
        score = 0.0
        
        # Нет визитов за 30 дней → +0.4
        if features["visits_30d"] == 0:
            score += 0.4
        elif features["visits_30d"] < 3:
            score += 0.2
        
        # Нет платежей за 90 дней → +0.3
        if features["payments_90d"] == 0:
            score += 0.3
        
        # Давно не был (30+ дней) → +0.3
        if features["last_visit_days"] > 30:
            score += 0.3
        elif features["last_visit_days"] > 14:
            score += 0.15
        
        # Абонемент скоро закончится (< 7 дней) → +0.2
        if features["subscription_days_left"] <= 7:
            score += 0.2
        elif features["subscription_days_left"] <= 3:
            score += 0.3
        
        # Нет активной подписки → +0.5
        if features["subscription_type"] == "none":
            score += 0.5
        
        return min(score, 1.0)
    
    def _get_risk_level(self, probability: float) -> str:
        """Определить уровень риска."""
        if probability >= self.RISK_THRESHOLDS["critical"]:
            return "critical"
        elif probability >= self.RISK_THRESHOLDS["high"]:
            return "high"
        elif probability >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        return "low"
    
    def batch_predict(self, client_ids: List[str]) -> List[Dict]:
        """Предсказать отток для списка клиентов."""
        return [self.predict(cid) for cid in client_ids]
    
    def needs_attention(self, client_id: str) -> bool:
        """Требует ли клиент внимания менеджера?"""
        result = self.predict(client_id)
        return result["risk_level"] in ("high", "critical")
