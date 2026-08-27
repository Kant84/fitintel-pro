# fitintel-desktop/ml/adaptive_ui.py
class AdaptiveUI:
    def __init__(self):
        self.user_patterns = {}  # {user_id: {clicks: Counter, avg_time: dict}}
    
    def reorder_sidebar(self, user_id: str) -> list:
        # Частые вкладки вверху
        return sorted(screens, key=lambda s: self.user_patterns[user_id].get(s, 0), reverse=True)
    
    def predict_next_action(self, user_id: str) -> str:
        # "Следующий экран: Клиенты" — подсказка в статус-баре
        ...