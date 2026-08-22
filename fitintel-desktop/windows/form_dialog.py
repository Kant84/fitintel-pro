"""FitIntel Pro — Generic Form Dialog"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox
)


class FormDialog(QDialog):
    """fields: list of (key, label, kind, options_or_default)
    kind: "text" | "combo"; combo options: list of (label, value)"""

    def __init__(self, title: str, fields: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self._widgets = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        for f in fields:
            key, label = f[0], f[1]
            kind = f[2] if len(f) > 2 else "text"
            if kind == "combo":
                w = QComboBox()
                for opt in (f[3] if len(f) > 3 else []):
                    if isinstance(opt, tuple):
                        w.addItem(str(opt[0]), opt[1])
                    else:
                        w.addItem(str(opt), opt)
            else:
                w = QLineEdit()
                if len(f) > 3 and f[3] not in (None, ""):
                    w.setText(str(f[3]))
            w.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px;")
            self._widgets[key] = (kind, w)
            form.addRow(label, w)
        layout.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def values(self) -> dict:
        out = {}
        for key, (kind, w) in self._widgets.items():
            out[key] = w.currentData() if kind == "combo" else w.text().strip()
        return out
