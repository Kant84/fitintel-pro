"""FitIntel Pro — Clients Tab (CRUD)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


class ClientsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            self.finished.emit(self.api.get_clients())
        except Exception as e:
            self.error.emit(str(e))


CLIENT_FIELDS = [
    ("last_name", "Фамилия *"),
    ("first_name", "Имя *"),
    ("middle_name", "Отчество"),
    ("phone", "Телефон *", "text", "+7"),
    ("email", "Email *"),
    ("gender", "Пол", "combo", [("Мужской", "MALE"), ("Женский", "FEMALE"), ("Не указан", "НЕ_УКАЗАН")]),
    ("birth_date", "Дата рождения (ГГГГ-ММ-ДД)"),
]

CAT_LABELS = {"ADULT": "Взрослый", "CHILD": "Ребёнок", "VIP": "VIP", "STAFF": "Персонал",
              "НЕ_УКАЗАНА": "—", "ПЕНСИОНЕР": "Пенсионер", "ИНВАЛИД": "Инвалид",
              "КОРПОРАТИВНЫЙ": "Корпоративный"}


class ClientsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._all_data = []
        self._build_ui()
        self.refresh()

    def _btn(self, text: str, color: str = "#f1f5f9", fg: str = "#475569") -> QPushButton:
        b = QPushButton(text)
        b.setStyleSheet(f"QPushButton {{ background: {color}; color: {fg}; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 14px; font-weight: 600; }}")
        return b

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("Поиск по ФИО, телефону, email...")
        self.edit_filter.setStyleSheet("QLineEdit { border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; min-width: 240px; }")
        self.edit_filter.textChanged.connect(self._filter)
        row.addWidget(self.edit_filter)
        row.addStretch()

        b_add = self._btn("＋ Добавить", "#10b981", "white")
        b_add.clicked.connect(self._add)
        row.addWidget(b_add)
        b_edit = self._btn("✎ Изменить")
        b_edit.clicked.connect(self._edit)
        row.addWidget(b_edit)
        b_deact = self._btn("⊘ Деактивировать", "#fee2e2", "#b91c1c")
        b_deact.clicked.connect(self._deactivate)
        row.addWidget(b_deact)
        b_del = self._btn("🗑 Удалить", "#dc2626", "white")
        b_del.clicked.connect(self._delete)
        row.addWidget(b_del)
        b_ref = self._btn("Обновить")
        b_ref.clicked.connect(self.refresh)
        row.addWidget(b_ref)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ФИО", "Телефон", "Email", "Категория", "Статус", "Создан"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        self.table.doubleClicked.connect(self._edit)
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = ClientsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _fio(self, c: dict) -> str:
        return " ".join(x for x in (c.get("last_name"), c.get("first_name"), c.get("middle_name")) if x) or "—"

    def _on_loaded(self, clients: list):
        self._all_data = clients
        self._render(clients)

    def _render(self, rows: list):
        self.table.setRowCount(len(rows))
        for i, c in enumerate(rows):
            item0 = QTableWidgetItem(self._fio(c))
            item0.setData(Qt.ItemDataRole.UserRole, str(c.get("id")))
            self.table.setItem(i, 0, item0)
            self.table.setItem(i, 1, QTableWidgetItem(str(c.get("phone") or "—")))
            self.table.setItem(i, 2, QTableWidgetItem(str(c.get("email") or "—")))
            self.table.setItem(i, 3, QTableWidgetItem(CAT_LABELS.get(str(c.get("client_category") or ""), str(c.get("client_category") or "—"))))
            active = c.get("is_active")
            item = QTableWidgetItem("Активен" if active else "Неактивен")
            item.setForeground(QColor("#059669" if active else "#ef4444"))
            self.table.setItem(i, 4, item)
            self.table.setItem(i, 5, QTableWidgetItem(str(c.get("created_at") or "")[:10]))

    def _filter(self, text: str):
        if not text:
            self._render(self._all_data)
            return
        t = text.lower()
        self._render([c for c in self._all_data
                      if t in f"{self._fio(c)} {c.get('phone', '')} {c.get('email', '')}".lower()])

    def _selected_client(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выбор", "Сначала выберите клиента в таблице")
            return None
        cid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for c in self._all_data:
            if str(c.get("id")) == cid:
                return c
        return None

    def _add(self):
        dlg = FormDialog("Новый клиент", CLIENT_FIELDS, self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["first_name"] or not v["last_name"] or not v["phone"] or not v["email"]:
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля: фамилия, имя, телефон, email")
            return
        payload = {k: val for k, val in v.items() if val not in ("", None)}
        try:
            self.api.create_client(payload)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка создания", str(e))

    def _edit(self):
        c = self._selected_client()
        if not c:
            return
        fields = [
            ("last_name", "Фамилия *", "text", c.get("last_name")),
            ("first_name", "Имя *", "text", c.get("first_name")),
            ("middle_name", "Отчество", "text", c.get("middle_name")),
            ("phone", "Телефон *", "text", c.get("phone")),
            ("email", "Email *", "text", c.get("email")),
            ("gender", "Пол", "combo", [("Мужской", "MALE"), ("Женский", "FEMALE"), ("Не указан", "НЕ_УКАЗАН")]),
            ("birth_date", "Дата рождения", "text", str(c.get("birth_date") or "")),
        ]
        dlg = FormDialog(f"Клиент: {self._fio(c)}", fields, self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val not in ("", None)}
        try:
            self.api.update_client(str(c["id"]), v)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _deactivate(self):
        c = self._selected_client()
        if not c:
            return
        reply = QMessageBox.question(self, "Деактивация",
                                     f"Деактивировать клиента {self._fio(c)}?")
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api.update_client(str(c["id"]), {"is_active": False, "status": "INACTIVE"})
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _delete(self):
        c = self._selected_client()
        if not c:
            return
        reply = QMessageBox.warning(
            self, "Удаление клиента",
            f"УДАЛИТЬ клиента {self._fio(c)} безвозвратно?\n\nЭто действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api.delete_client(str(c["id"]))
            try:
                from app_logging import log as _log
                _log.info("Удалён клиент %s (%s)", self._fio(c), c.get("id"))
            except Exception:
                pass
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
