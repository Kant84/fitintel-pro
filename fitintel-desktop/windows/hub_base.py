"""W5: базовый хаб с ЛЕНИВЫМИ подвкладками.
Подвкладка строится при первом открытии. ВАЖНО: _build защищён от реентерабельности —
_currentChanged заблокирован на время remove/insert, отметка о постройке ставится ДО
мутации (иначе setCurrentIndex перезапускает _build -> бесконечный цикл -> зависание)."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel


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
        for title, _fn in specs:
            self.tabs.addTab(QWidget(), title)   # placeholder
        self.tabs.currentChanged.connect(self._build)
        self._build(0)

    def _build(self, index: int):
        if index in self._built or not (0 <= index < len(self._specs)):
            return
        self._built.add(index)                    # ОТМЕТКА ДО мутации — защита от реентерабельности
        title, fn = self._specs[index]
        try:
            widget = fn()
        except Exception as e:
            widget = QLabel(f"Не удалось загрузить «{title}»: {e}")
        try:
            from windows.icons import polish
            polish(widget)
        except Exception:
            pass
        self.tabs.blockSignals(True)              # remove/insert не дёргают currentChanged
        try:
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, widget, title)
            if self.tabs.currentIndex() < 0:
                self.tabs.setCurrentIndex(index)
        finally:
            self.tabs.blockSignals(False)

    def refresh(self):
        w = self.tabs.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()


print("[hub_base] W5 v2.1 загружен: ленивые хабы (reentrancy-safe)")