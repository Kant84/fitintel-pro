"""FitIntel Pro — UI-Config Tab (матрица роль → экраны)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from api import ApiClient
from windows import theme


class UiConfigWorker(QThread):
    finished = pyqtSignal(list, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            screens = self.api.get_ui_screens()
            roles = self.api.get_ui_roles()
            self.finished.emit(screens, roles)
        except Exception as e:
            self.error.emit(str(e))


ROLE_LABELS = {
    "superadmin": "Суперадминистратор",
    "admin": "Администратор",
    "manager": "Менеджер",
    "trainer": "Тренер",
    "reception": "Ресепшен",
}


class UiConfigTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._screens = []
        self._matrix = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(QLabel("Роль:"))
        self.cmb_role = QComboBox()
        for r in ("superadmin", "admin", "manager", "trainer", "reception"):
            self.cmb_role.addItem(ROLE_LABELS.get(r, r), r)
        self.cmb_role.currentIndexChanged.connect(self._render_table)
        self.cmb_role.setStyleSheet("padding: 6px; min-width: 180px;")
        top.addWidget(self.cmb_role)
        top.addStretch()

        btn_save = QPushButton("Сохранить")
        btn_save.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: 600; }")
        btn_save.clicked.connect(self._save)
        top.addWidget(btn_save)

        btn_reset = QPushButton("Сбросить к умолчаниям")
        btn_reset.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_reset.clicked.connect(self._reset)
        top.addWidget(btn_reset)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_refresh.clicked.connect(self.refresh)
        top.addWidget(btn_refresh)
        layout.addLayout(top)

        self.lbl_hint = QLabel("Отметьте экраны, которые будут видны выбранной роли в тонком клиенте")
        self.lbl_hint.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_hint)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Виден", "Экран", "Код"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = UiConfigWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, screens: list, roles: dict):
        self._screens = screens
        self._matrix = roles.get("roles", {})
        self._render_table()

    def _current_visibility(self, role: str) -> set:
        return {s["screen_code"] for s in self._matrix.get(role, []) if s.get("is_visible")}

    def _render_table(self):
        role = self.cmb_role.currentData()
        visible = self._current_visibility(role)
        self.table.setRowCount(len(self._screens))
        for i, s in enumerate(self._screens):
            chk = QCheckBox()
            chk.setChecked(s["code"] in visible)
            if role == "superadmin" and s["code"] == "ui_config":
                chk.setEnabled(False)
                chk.setToolTip("Защита от самоблокировки: у суперадмина всегда виден")
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(12, 0, 0, 0)
            hl.addWidget(chk)
            hl.addStretch()
            self.table.setCellWidget(i, 0, w)
            self.table.setItem(i, 1, QTableWidgetItem(s.get("name", s["code"])))
            self.table.setItem(i, 2, QTableWidgetItem(s["code"]))

    def _collect_visible(self) -> list:
        codes = []
        for i, s in enumerate(self._screens):
            w = self.table.cellWidget(i, 0)
            chk = w.findChild(QCheckBox)
            if chk and chk.isChecked():
                codes.append(s["code"])
        return codes

    def _save(self):
        role = self.cmb_role.currentData()
        try:
            res = self.api.set_ui_role_screens(role, self._collect_visible())
            QMessageBox.information(self, "Сохранено",
                f"Роль {ROLE_LABELS.get(role, role)}: видимых {res.get('visible')}, скрытых {res.get('hidden')}")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _reset(self):
        role = self.cmb_role.currentData()
        reply = QMessageBox.question(self, "Сброс",
            f"Сбросить экраны роли {ROLE_LABELS.get(role, role)} к умолчаниям?")
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api.reset_ui_role(role)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 1, QTableWidgetItem(f"Ошибка загрузки (нужны права admin/superadmin): {msg}"))
