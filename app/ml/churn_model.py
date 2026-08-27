# app/ml/churn_model.py
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split

class ChurnModel:
    def __init__(self):
        self.model = XGBClassifier()
        self.retrain_threshold = 100  # новых записей для переобучения
    
    def predict(self, client_features: dict) -> float:
        # Возвращает вероятность оттока 0..1
        return self.model.predict_proba([client_features])[0][1]
    
    def retrain(self, new_data):
        # Авто-переобучение при накоплении данных
        self.model.fit(X, y)
        joblib.dump(self.model, "models/churn_v{version}.pkl")