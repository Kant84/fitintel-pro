"""W5: базовый хаб с ЛЕНИВЫМИ подвкладками.
Подвкладка строится при первом открытии (как вкладки в main_window):
нет лавины сетевых запросов при старте, нет зависаний. При постройке
прогоняется polish() — неон-иконки на кнопках подвкладки."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget


class HubTab(QWidget):
    def __init__(self, api, specs, main_window=None):
        """specs: список (заголовок, builder_fn). builder_fn() -> QWidget."""
        super().__init__()
        self.api = api
        self._specs = specs
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        lay.addWidget(self.tabs)
        self._built = set()
        for i, (title, _fn) in enumerate(specs):
            self.tabs.addTab(QWidget(), title)   # placeholder
        self.tabs.currentChanged.connect(self._build)
        self._build(0)

    def _build(self, index: int):
        if index in self._built or not (0 <= index < len(self._specs)):
            return
        title, fn = self._specs[index]
        try:
            widget = fn()
        except Exception as e:
            from PyQt6.QtWidgets import QLabel
            widget = QLabel(f"Не удалось загрузить «{title}»: {e}")
        try:
            from windows.icons import polish
            polish(widget)
        except Exception:
            pass
        cur = self.tabs.currentIndex()
        self.tabs.removeTab(index)
        self.tabs.insertTab(index, widget, title)
        self.tabs.setCurrentIndex(cur if cur >= 0 else 0)
        self._built.add(index)

    def refresh(self):
        """F5: обновить текущую подвкладку, если умеет."""
        w = self.tabs.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()