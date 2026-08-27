# app/ml/send_time_optimizer.py
# Кластеризуем клиентов по активности и подбираем индивидуальное время
from sklearn.cluster import KMeans

def get_optimal_send_time(client_id: str) -> str:
    # Возвращает "09:30" или "19:45" на основе истории открытий
    ...