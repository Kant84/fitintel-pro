"""FitIntel Pro — Documents Tab (шаблоны + документы)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from PyQt6.QtWidgets import QMessageBox

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


class DocumentsWorker(QThread):
    finished = pyqtSignal(list, list, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            resp = self.api.session.get(self.api._url("/documents"))
            resp.raise_for_status()
            docs = resp.json().get("documents", [])
            resp2 = self.api.session.get(self.api._url("/documents/templates"))
            resp2.raise_for_status()
            tpls = resp2.json().get("templates", [])
            clients = self.api.get_clients()
            cmap = {}
            for c in clients:
                fio = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x)
                cmap[str(c.get("id"))] = fio or "—"
            self.finished.emit(docs, tpls, cmap)
        except Exception as e:
            self.error.emit(str(e))


class DocumentsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        row = QHBoxLayout()
        row.addStretch()
        b_gen = QPushButton("Сгенерировать")
        b_gen.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_gen.clicked.connect(self._generate)
        row.addWidget(b_gen)
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        box_t = QGroupBox("Шаблоны документов")
        tl = QVBoxLayout(box_t)
        self.tbl_tpl = QTableWidget()
        self.tbl_tpl.setColumnCount(2)
        self.tbl_tpl.setHorizontalHeaderLabels(["Код", "Название"])
        self.tbl_tpl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_tpl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_tpl.setMaximumHeight(140)
        tl.addWidget(self.tbl_tpl)
        layout.addWidget(box_t)

        box_d = QGroupBox("Документы")
        dl = QVBoxLayout(box_d)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Тип", "Клиент", "Статус", "Создан"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        dl.addWidget(self.table)
        layout.addWidget(box_d)

    def refresh(self):
        self.worker = DocumentsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, docs: list, tpls: list, cmap: dict):
        self._tpls = tpls
        self._cmap = cmap
        self.tbl_tpl.setRowCount(len(tpls))
        for i, t in enumerate(tpls):
            self.tbl_tpl.setItem(i, 0, QTableWidgetItem(str(t.get("code") or "—")))
            self.tbl_tpl.setItem(i, 1, QTableWidgetItem(str(t.get("name") or "—")))

        self.table.setRowCount(max(len(docs), 1))
        if not docs:
            self.table.setItem(0, 0, QTableWidgetItem("Документов пока нет"))
            return
        for i, d in enumerate(docs):
            self.table.setItem(i, 0, QTableWidgetItem(str(d.get("title") or "—")))
            self.table.setItem(i, 1, QTableWidgetItem(str(d.get("type") or "—")))
            self.table.setItem(i, 2, QTableWidgetItem(cmap.get(str(d.get("client_id")), "—")))
            st = str(d.get("status") or "—")
            if d.get("signed"):
                st += " (подписан)"
            item = QTableWidgetItem(st)
            if d.get("signed"):
                item.setForeground(QColor("#059669"))
            self.table.setItem(i, 3, item)
            self.table.setItem(i, 4, QTableWidgetItem(str(d.get("created_at") or "")[:10]))

    def _generate(self):
        tpls = getattr(self, "_tpls", [])
        cmap = getattr(self, "_cmap", {})
        if not tpls or not cmap:
            QMessageBox.warning(self, "Нет данных", "Нужны шаблоны и клиенты")
            return
        dlg = FormDialog("Новый документ", [
            ("template", "Шаблон *", "combo",
             [(t.get("name", t.get("code")), (t.get("template_id"), t.get("code"))) for t in tpls]),
            ("client_id", "Клиент *", "combo",
             [(v, k) for k, v in list(cmap.items())[:200]]),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        tpl_id, tpl_code = v["template"]
        payload = {"type": tpl_code, "client_id": v["client_id"], "template_id": tpl_id}
        try:
            r = self.api.session.post(self.api._url("/documents"), json=payload)
            r.raise_for_status()
            QMessageBox.information(self, "Готово", "Документ создан")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
