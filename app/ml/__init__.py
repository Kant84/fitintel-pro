"""E60: ML-модули FitIntel Pro."""
from app.ml.event_logger import EventLogger
from app.ml.feature_store import FeatureStore
from app.ml.churn_model import ChurnModel

__all__ = ["EventLogger", "FeatureStore", "ChurnModel"]
