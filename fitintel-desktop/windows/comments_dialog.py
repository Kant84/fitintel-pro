# -*- coding: utf-8 -*-
"""Диалог «Все комментарии» (только для руководителей). Эндпоинт /comments — TODO на FastAPI."""
import requests as _requests
import windows.theme as theme
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView)
from windows.icons import icon as _icon, polish as _polish
from app_logging import log


class CommentsDialog(QDialog):
    def __init__(self, api, user_data=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.user_data = user_data or {}

        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Все комментарии")
        self.resize(1000, 700)
        self._users = []
        self._build_ui()
        self._load_users()
        self._reload()
        _polish(self)
        from windows.help_dialog import install_f1
        install_f1(self, "comments")

    def _build_ui(self):
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Автор:"))
        self._cb_author = QComboBox()
        self._cb_author.addItem("Все", None)
        top.addWidget(self._cb_author)
        top.addWidget(QLabel("Тип:"))
        self._cb_type = QComboBox()
        self._cb_type.addItem("Все", None)
        self._cb_type.addItem("Заметка", "NOTE")
        self._cb_type.addItem("Задача", "TASK")
        self._cb_type.addItem("Звонок", "CALL")
        top.addWidget(self._cb_type)
        top.addWidget(QLabel("От:"))
        self._dt_from = QDateEdit(QDate.currentDate().addDays(-30))
        self._dt_from.setCalendarPopup(True)
        top.addWidget(self._dt_from)
        top.addWidget(QLabel("До:"))
        self._dt_to = QDateEdit(QDate.currentDate())
        self._dt_to.setCalendarPopup(True)
        top.addWidget(self._dt_to)
        b_ref = QPushButton(" Обновить")
        b_ref.setStyleSheet("background: #10b981; color: white; border: none; "
                            "border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_ref.clicked.connect(self._reload)
        top.addWidget(b_ref)
        top.addStretch(1)
        v.addLayout(top)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(["Дата", "Автор", "Клиент", "Тип", "Текст", "Срок", "Статус"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(theme.table_style())
        self._table.itemDoubleClicked.connect(self._open_client)
        v.addWidget(self._table, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        for fmt, label in [("xlsx", "XLSX"), ("pdf", "PDF")]:
            b = QPushButton(label)
            b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; "
                            "border: 1px solid #cbd5e1; border-radius: 6px; "
                            "padding: 6px 12px; font-weight: 600; }")
            b.clicked.connect(lambda _, f=fmt: self._export(f))
            bottom.addWidget(b)
        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.accept)
        bottom.addWidget(b_close)
        v.addLayout(bottom)

    # ---------- загрузка ----------
    def _load_users(self):
        class _W(QThread):
            done = pyqtSignal(list)
            def __init__(self, api):
                super().__init__(); self.api = api
            def run(self):
                try:
                    self.done.emit(self.api.get_users())
                except Exception:
                    self.done.emit([])
        self._wu = _W(self.api)
        self._wu.done.connect(self._fill_users)
        self._wu.start()

    def _fill_users(self, users):
        self._users = users or []
        cur = self._cb_author.currentData()
        self._cb_author.clear()
        self._cb_author.addItem("Все", None)
        for u in self._users:
            name = u.get("full_name") or u.get("username") or "—"
            self._cb_author.addItem(name, u.get("id"))
        idx = self._cb_author.findData(cur)
        if idx >= 0:
            self._cb_author.setCurrentIndex(idx)

    def _reload(self):
        params = {
            "from": self._dt_from.date().toString("yyyy-MM-dd"),
            "to": self._dt_to.date().toString("yyyy-MM-dd"),
        }
        if self._cb_type.currentData():
            params["type"] = self._cb_type.currentData()
        if self._cb_author.currentData():
            params["author_id"] = self._cb_author.currentData()

        class _W(QThread):
            done = pyqtSignal(object)
            err = pyqtSignal(str)
            def __init__(self, api, params):
                super().__init__(); self.api = api; self.params = params
            def run(self):
                try:
                    self.done.emit(self.api._e55_get("/comments", self.params))
                except Exception as e:
                    self.err.emit(str(e))
        self._w = _W(self.api, params)
        self._w.done.connect(self._fill)
        self._w.err.connect(self._on_err)
        self._w.start()

    def _fill(self, resp):
        self._table.setRowCount(0)
        items = (resp.get("items", []) if isinstance(resp, dict)
                 else (resp if isinstance(resp, list) else []))
        for c in items:
            if not isinstance(c, dict):
                continue
            r = self._table.rowCount()
            self._table.insertRow(r)
            vals = [
                str(c.get("created_at") or "")[:16],
                str(c.get("author_name") or "—"),
                str(c.get("client_id") or "—")[:8],
                str(c.get("type") or "NOTE"),
                str(c.get("text") or "")[:80],
                str(c.get("due_date") or "—")[:10],
                str(c.get("status") or "—"),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 2 and c.get("client_id"):
                    item.setData(Qt.ItemDataRole.UserRole, str(c.get("client_id")))
                self._table.setItem(r, col, item)

    def _on_err(self, msg):
        self._table.setRowCount(0)
        self._table.insertRow(0)
        text = ("Раздел в разработке — эндпоинт /comments"
                if ("404" in msg or "not found" in msg.lower()) else f"Ошибка: {msg}")
        self._table.setItem(0, 0, QTableWidgetItem(text))

    def _open_client(self, item):
        cid = item.data(Qt.ItemDataRole.UserRole)
        if not cid:
            return
        from windows.client_card import ClientCard
        dlg = ClientCard(self.api, cid, user_data=self.user_data, parent=None)
        dlg.show()

    def _export(self, fmt):
        from windows.export_helper import export_table_xlsx, export_table_pdf
        headers = [self._table.horizontalHeaderItem(i).text() for i in range(self._table.columnCount())]
        rows = [[self._table.item(r, c).text() if self._table.item(r, c) else ""
                 for c in range(self._table.columnCount())] for r in range(self._table.rowCount())]
        try:
            if fmt == "xlsx":
                export_table_xlsx(self, headers, rows, "comments", "Все комментарии")
            else:
                export_table_pdf(self, headers, rows, "comments", "Все комментарии")
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.warning(self, "Экспорт", str(e)[:200])