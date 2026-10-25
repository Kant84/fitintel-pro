# fitintel-desktop/ml/adaptive_ui.py
class AdaptiveUI:
    def __init__(self):
        self.user_patterns = {}  # {user_id: {clicks: Counter, avg_time: dict}}
    
    def reorder_sidebar(self, user_id: str, screens: list = None) -> list:
        # Частые вкладки вверху; неизвестный пользователь не вызывает ошибку.
        if screens is None:
            screens = list(self.user_patterns.get(user_id, {}))
        patterns = self.user_patterns.get(user_id, {})
        return sorted(screens, key=lambda s: patterns.get(s, 0), reverse=True)
    
    def predict_next_action(self, user_id: str) -> str:
        # "Следующий экран: Клиенты" — подсказка в статус-баре
        ...