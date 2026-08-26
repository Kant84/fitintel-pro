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
            resp2 = self.api.session.get(self.api._url("/document-templates"))
            resp2.raise_for_status()
            _tpls_raw = resp2.json()
            tpls = _tpls_raw.get("templates", []) if isinstance(_tpls_raw, dict) else _tpls_raw
            clients = self.api.get_clients()
            if isinstance(clients, dict):
                clients = clients.get("items", []) or clients.get("clients", [])
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
        b_sign = QPushButton("✍ Подписать")
        b_sign.setStyleSheet("QPushButton { background: #E6007E; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_sign.clicked.connect(self._sign_doc)
        row.addWidget(b_sign)
        b_dl = QPushButton("📥 PDF")
        b_dl.setStyleSheet("QPushButton { background: #3B82F6; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_dl.clicked.connect(self._download_pdf)
        row.addWidget(b_dl)
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
            it0 = QTableWidgetItem(str(d.get("title") or "—"))
            it0.setData(Qt.ItemDataRole.UserRole, str(d.get("document_id") or ""))
            self.table.setItem(i, 0, it0)
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

    def _sign_doc(self):
        row = self.table.currentRow()
        if row < 0:
            return
        doc_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not doc_id:
            QMessageBox.warning(self, "Подпись", "ID документа не найден")
            return
        try:
            r = self.api.session.post(self.api._url(f"/documents/{doc_id}/sign"), json={})
            r.raise_for_status()
            d = r.json()
            QMessageBox.information(self, "Подпись", d.get("message", "Подписано"))
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подписи", str(e)[:200])

    def _download_pdf(self):
        row = self.table.currentRow()
        if row < 0:
            return
        doc_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not doc_id:
            QMessageBox.warning(self, "PDF", "ID документа не найден")
            return
        try:
            r = self.api.session.get(self.api._url(f"/documents/{doc_id}/download?format=pdf"))
            r.raise_for_status()
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить PDF", f"doc_{doc_id}.pdf", "PDF (*.pdf)")
            if path:
                with open(path, "wb") as f:
                    f.write(r.content)
                QMessageBox.information(self, "PDF", f"Сохранено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:200])

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))


# === E59B: create template button ===
def create_template_dialog(self):
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPlainTextEdit, QPushButton, QLabel, QMessageBox
    d = QDialog(self)
    d.setWindowTitle("Новый шаблон документа")
    lay = QVBoxLayout(d)
    lay.addWidget(QLabel("Название шаблона:"))
    ed_name = QLineEdit(); lay.addWidget(ed_name)
    lay.addWidget(QLabel("Тип:"))
    cb = QComboBox(); cb.addItems(["contract", "act", "agreement", "scan", "receipt", "other"]); lay.addWidget(cb)
    lay.addWidget(QLabel("Текст шаблона (можно использовать {client}, {tariff}, {days}):"))
    ed_body = QPlainTextEdit(); lay.addWidget(ed_body)
    btns = QHBoxLayout()
    ok = QPushButton("💾 Сохранить шаблон"); cancel = QPushButton("Отмена")
    btns.addWidget(ok); btns.addWidget(cancel); lay.addLayout(btns)
    cancel.clicked.connect(d.reject)
    def _save():
        if not ed_name.text().strip():
            QMessageBox.warning(d, "Шаблон", "Введите название"); return
        try:
            self.api._e55_post("/document-templates", {"name": ed_name.text().strip(), "doc_type": cb.currentText(), "content": ed_body.toPlainText()})
            QMessageBox.information(d, "Шаблон", "Шаблон сохранён! Теперь он доступен в кнопке «📄 Из шаблона».")
            d.accept()
        except Exception as e:
            QMessageBox.critical(d, "Ошибка", str(e))
    ok.clicked.connect(_save)
    d.resize(560, 480)
    d.exec()

try:
    DocumentsTab.create_template_dialog = create_template_dialog
    _orig_init = DocumentsTab.__init__
    def _patched_init(self, *a, **kw):
        _orig_init(self, *a, **kw)
        try:
            from PyQt6.QtWidgets import QPushButton
            btn = QPushButton("📝 Создать шаблон")
            btn.clicked.connect(self.create_template_dialog)
            for b in self.findChildren(QPushButton):
                if "шаблон" in b.text().lower():
                    b.parentWidget().layout().addWidget(btn) if b.parentWidget() and b.parentWidget().layout() else None
                    break
            else:
                self.layout().addWidget(btn)
        except Exception as e:
            print("template btn:", e)
    DocumentsTab.__init__ = _patched_init
except Exception as e:
    print("patch:", e)


# === E63_PRINT ===
try:
    from windows.print_helper import add_print_button as _e63_apb
    _e63_orig = DocumentsTab.__init__
    def _e63_init(self, *a, **kw):
        _e63_orig(self, *a, **kw)
        try:
            _e63_apb(self, "Документы")
        except Exception as e:
            print("print btn:", e)
    DocumentsTab.__init__ = _e63_init
    print("E63 print OK: documents_tab.py")
except Exception as e:
    print("E63 FAIL:", e)
