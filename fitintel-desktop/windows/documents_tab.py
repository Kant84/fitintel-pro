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
        b_sign = QPushButton(" Подписать")
        b_sign.setStyleSheet("QPushButton { background: #E6007E; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_sign.clicked.connect(self._sign_doc)
        row.addWidget(b_sign)
        b_dl = QPushButton(" PDF")
        b_dl.setStyleSheet("QPushButton { background: #3B82F6; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_dl.clicked.connect(self._download_pdf)
        row.addWidget(b_dl)
        self._btn_tpl = QPushButton(" Шаблоны")
        self._btn_doc = QPushButton(" Документы")
        self._btn_tpl.setCheckable(True)
        self._btn_doc.setCheckable(True)
        self._btn_doc.setChecked(True)
        self._btn_tpl.clicked.connect(lambda: self._switch_tab("tpl"))
        self._btn_doc.clicked.connect(lambda: self._switch_tab("doc"))
        row.addWidget(self._btn_tpl)
        row.addWidget(self._btn_doc)
        layout.addLayout(row)

        box_t = QGroupBox("Шаблоны документов")
        tl = QVBoxLayout(box_t)
        self.tbl_tpl = QTableWidget()
        self.tbl_tpl.setColumnCount(2)
        self.tbl_tpl.setHorizontalHeaderLabels(["Код", "Название"])
        self.tbl_tpl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_tpl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # self.tbl_tpl.setMaximumHeight(140)  # E16D: full height
        tl.addWidget(self.tbl_tpl)
        tl.addStretch(1)
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
        if not tpls:
            QMessageBox.warning(self, "Нет шаблонов", "Шаблоны документов не загружены. Нажмите Обновить.")
            return
        if not cmap:
            QMessageBox.warning(self, "Нет клиентов", "В базе нет клиентов. Добавьте клиента в разделе Клиенты.")
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

    def _switch_tab(self, mode):
        self._btn_tpl.setChecked(mode == "tpl")
        self._btn_doc.setChecked(mode == "doc")
        # Находим group boxes
        for gb in self.findChildren(QGroupBox):
            if "Шаблоны" in gb.title():
                gb.setVisible(mode == "tpl")
            elif "Документы" in gb.title():
                gb.setVisible(mode == "doc")

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
    ok = QPushButton(" Сохранить шаблон"); cancel = QPushButton("Отмена")
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
            btn = QPushButton(" Создать шаблон")
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


# === скрыть дубль «В PDF» (E63) ===
try:
    import inspect as _i2
    from PyQt6.QtWidgets import QWidget as _W2, QPushButton as _PB2
    for _n, _o in list(globals().items()):
        if (_i2.isclass(_o) and issubclass(_o, _W2)
                and getattr(_o, "__module__", "") == __name__ and not _n.startswith("_")):
            _oi = _o.__init__
            def _mk2(orig):
                def _ii(self, *a, **k):
                    orig(self, *a, **k)
                    try:
                        for b in self.findChildren(_PB2):
                            if b.text().strip() == "В PDF":
                                b.setVisible(False)
                    except Exception:
                        pass
                return _ii
            _o.__init__ = _mk2(_oi)
    print("PDF cleanup OK: documents_tab")
except Exception as _e:
    print("PDF cleanup FAIL:", _e)

# === W16_WORD_DOCS: двойной клик + Word (.doc) + fallback PDF ===
def _doc_text(self, doc_id):
    r = self.api.session.get(self.api._url("/documents/%s" % doc_id), timeout=20)
    r.raise_for_status()
    try:
        d = r.json()
        return str(d.get("content") or d.get("body") or d.get("text") or d.get("document", {}).get("content") or "")
    except Exception:
        return r.text


def _open_word(self, text, prefix="doc"):
    import os, html, tempfile
    path = os.path.join(tempfile.gettempdir(), "%s_%d.doc" % (prefix, abs(hash(str(text))) % 99999))
    h = ('<html><head><meta charset="utf-8"></head><body '
         'style="font-family:Times New Roman;font-size:12pt">'
         '<pre style="white-space:pre-wrap">%s</pre></body></html>') % html.escape(str(text) or "(пусто)")
    open(path, "w", encoding="utf-8").write(h)
    os.startfile(path)


def _tpl_dbl(self, item):
    row = self.tbl_tpl.currentRow()
    if row < 0:
        return
    tpls = getattr(self, "_tpls", []) or []
    if row >= len(tpls):
        return
    t = tpls[row]
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton
    d = QDialog(self)
    d.setWindowTitle("Шаблон: " + str(t.get("name") or ""))
    lay = QVBoxLayout(d)
    lay.addWidget(QLabel("Код: %s   |   Тип: %s" % (t.get("code") or "—", t.get("doc_type") or "—")))
    te = QPlainTextEdit()
    te.setReadOnly(True)
    te.setPlainText(str(t.get("content") or "(список шаблонов не отдаёт текст — текст подставится при генерации документа)"))
    lay.addWidget(te, 1)
    b = QPushButton("Закрыть")
    b.clicked.connect(d.accept)
    lay.addWidget(b)
    d.resize(620, 480)
    d.exec()


def _doc_dbl(self, item):
    row = self.table.currentRow()
    if row < 0:
        return
    doc_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
    if not doc_id:
        return
    try:
        self._open_word(self._doc_text(doc_id), "doc_%s" % str(doc_id)[:8])
    except Exception as e:
        QMessageBox.critical(self, "Документ", str(e)[:200])


def _generate_w16(self):
    tpls = getattr(self, "_tpls", [])
    cmap = getattr(self, "_cmap", {})
    if not tpls:
        QMessageBox.warning(self, "Нет шаблонов", "Шаблоны документов не загружены. Нажмите Обновить.")
        return
    if not cmap:
        QMessageBox.warning(self, "Нет клиентов", "В базе нет клиентов. Добавьте клиента в разделе Клиенты.")
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
        d = r.json() or {}
        doc_id = d.get("document_id") or d.get("id") or d.get("doc_id") or (d.get("document") or {}).get("id")
        self.refresh()
        if doc_id:
            try:
                self._open_word(self._doc_text(doc_id), "doc_%s" % str(doc_id)[:8])
                return
            except Exception:
                pass
        QMessageBox.information(self, "Готово", "Документ создан. Откройте его двойным кликом.")
    except Exception as e:
        QMessageBox.critical(self, "Ошибка", str(e))


def _download_pdf_w16(self):
    row = self.table.currentRow()
    if row < 0:
        return
    doc_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
    if not doc_id:
        QMessageBox.warning(self, "PDF", "ID документа не найден")
        return
    try:
        r = self.api.session.get(self.api._url("/documents/%s/download?format=pdf" % doc_id))
        r.raise_for_status()
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить PDF", "doc_%s.pdf" % doc_id[:8], "PDF (*.pdf)")
        if path:
            with open(path, "wb") as fh:
                fh.write(r.content)
            QMessageBox.information(self, "PDF", "Сохранено: %s" % path)
    except Exception as e:
        try:
            self._open_word(self._doc_text(doc_id), "doc_%s" % str(doc_id)[:8])
            QMessageBox.information(
                self, "PDF недоступен",
                "Сервер не отдал PDF (%s).\nДокумент открыт в Word — сохраните как PDF из Word." % str(e)[:90])
        except Exception as e2:
            QMessageBox.critical(self, "Ошибка", str(e2)[:200])


DocumentsTab._doc_text = _doc_text
DocumentsTab._open_word = _open_word
DocumentsTab._generate = _generate_w16
DocumentsTab._download_pdf = _download_pdf_w16

_w16_orig_init = DocumentsTab.__init__
def _w16_init(self, *a, **kw):
    _w16_orig_init(self, *a, **kw)
    try:
        self.tbl_tpl.itemDoubleClicked.connect(self._tpl_dbl)
        self.table.itemDoubleClicked.connect(self._doc_dbl)
    except Exception as e:
        print("W16 dbl:", e)
DocumentsTab.__init__ = _w16_init

# === W17_EDIT_TPL: редактирование шаблона по двойному клику ===
def _tpl_dbl_edit(self, item):
    row = self.tbl_tpl.currentRow()
    if row < 0:
        return
    tpls = getattr(self, "_tpls", []) or []
    if row >= len(tpls):
        return
    t = dict(tpls[row])
    tid = t.get("template_id") or t.get("id")
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton
    d = QDialog(self)
    d.setWindowTitle("Шаблон: " + str(t.get("name") or ""))
    lay = QVBoxLayout(d)
    lay.addWidget(QLabel("Название:"))
    ed_name = QLineEdit(str(t.get("name") or ""))
    lay.addWidget(ed_name)
    lay.addWidget(QLabel("Текст (переменные: {{client_name}} {{phone}} {{email}} {{tariff}} {{date}} {{club_name}}):"))
    te = QPlainTextEdit()
    te.setPlainText(str(t.get("content") or ""))
    lay.addWidget(te, 1)
    bar = QHBoxLayout()
    b_save = QPushButton(" Сохранить")
    b_close = QPushButton("Закрыть")
    bar.addWidget(b_save)
    bar.addWidget(b_close)
    lay.addLayout(bar)
    b_close.clicked.connect(d.reject)

    def _save():
        if not ed_name.text().strip():
            QMessageBox.warning(d, "Шаблон", "Введите название")
            return
        payload = {"name": ed_name.text().strip(), "content": te.toPlainText()}
        url = self.api._url("/document-templates/%s" % tid)
        ok = False
        for meth in ("put", "patch"):
            try:
                r = getattr(self.api.session, meth)(url, json=payload, timeout=20)
                if r.status_code in (200, 204):
                    ok = True
                    break
            except Exception:
                pass
        if ok:
            QMessageBox.information(d, "Шаблон", "Сохранено")
            d.accept()
            self.refresh()
        else:
            QMessageBox.critical(d, "Шаблон",
                "Сервер не принял изменения (нет метода PUT/PATCH для шаблонов).\n"
                "Удалите шаблон и создайте заново с тем же текстом.")
    b_save.clicked.connect(_save)
    d.resize(680, 560)
    d.exec()

DocumentsTab._tpl_dbl_edit = _tpl_dbl_edit

_w17_orig_init = DocumentsTab.__init__
def _w17_init(self, *a, **kw):
    _w17_orig_init(self, *a, **kw)
    try:
        self.tbl_tpl.itemDoubleClicked.disconnect()
    except Exception:
        pass
    try:
        self.tbl_tpl.itemDoubleClicked.connect(self._tpl_dbl_edit)
    except Exception as e:
        print("W17:", e)
DocumentsTab.__init__ = _w17_init

# === W18_UPLOAD_TPL: загрузка шаблона из файла ===
def _upload_template(self):
    from PyQt6.QtWidgets import QFileDialog
    path, _ = QFileDialog.getOpenFileName(self, "Загрузить шаблон", "", "Шаблоны (*.docx *.txt)")
    if not path:
        return
    base_name = path.replace("\\", "/").split("/")[-1]
    try:
        with open(path, "rb") as fh:
            r = self.api.session.post(
                self.api._url("/document-templates/upload"),
                files={"file": (base_name, fh, "application/octet-stream")},
                data={"name": base_name.rsplit(".", 1)[0], "doc_type": "other"},
                timeout=30)
        if r.status_code in (200, 201):
            QMessageBox.information(self, "Шаблон",
                "Загружено: %s (код %s)" % (base_name, r.json().get("code", "?")))
            self.refresh()
        else:
            QMessageBox.critical(self, "Шаблон", str(r.text)[:200])
    except Exception as e:
        QMessageBox.critical(self, "Шаблон", str(e)[:200])

DocumentsTab._upload_template = _upload_template

_w18_orig_init = DocumentsTab.__init__
def _w18_init(self, *a, **kw):
    _w18_orig_init(self, *a, **kw)
    try:
        b = QPushButton(" Загрузить шаблон")
        b.clicked.connect(self._upload_template)
        placed = False
        for bb in self.findChildren(QPushButton):
            if "создать шаблон" in bb.text().lower():
                lay = bb.parentWidget().layout()
                if lay is not None:
                    lay.addWidget(b)
                    placed = True
                    break
        if not placed:
            self.layout().addWidget(b)
    except Exception as e:
        print("W18:", e)
DocumentsTab.__init__ = _w18_init

# === W19_COMPACT_UI: без тумблеров, поиск, компактные кнопки, скроллы ===
def _w19_filter_rows(tbl, text):
    text = (text or "").lower().strip()
    for r in range(tbl.rowCount()):
        show = not text
        if not show:
            for c in range(tbl.columnCount()):
                it = tbl.item(r, c)
                if it is not None and text in it.text().lower():
                    show = True
                    break
        tbl.setRowHidden(r, not show)


def _w19_apply(self):
    from PyQt6.QtWidgets import QLineEdit
    from PyQt6.QtCore import Qt
    # 1. убрать тумблеры «Шаблоны/Документы», показать оба блока
    for b in self.findChildren(QPushButton):
        if b.text().strip() in ("Шаблоны", "Документы"):
            b.setVisible(False)
    for gb in self.findChildren(QGroupBox):
        gb.setVisible(True)
    # 2. поиск по обоим спискам
    if not hasattr(self, "_w19_s_tpl"):
        self._w19_s_tpl = QLineEdit()
        self._w19_s_tpl.setPlaceholderText("Поиск по шаблонам...")
        self._w19_s_tpl.setMaximumHeight(26)
        self.tbl_tpl.parentWidget().layout().insertWidget(0, self._w19_s_tpl)
        self._w19_s_tpl.textChanged.connect(lambda s: _w19_filter_rows(self.tbl_tpl, s))
        self._w19_s_doc = QLineEdit()
        self._w19_s_doc.setPlaceholderText("Поиск по документам (название/клиент/статус)...")
        self._w19_s_doc.setMaximumHeight(26)
        self.table.parentWidget().layout().insertWidget(0, self._w19_s_doc)
        self._w19_s_doc.textChanged.connect(lambda s: _w19_filter_rows(self.table, s))
    # 3. компактные кнопки снизу + ограниченные высоты списков со скроллами
    for b in self.findChildren(QPushButton):
        lt = b.text().lower()
        if "создать шаблон" in lt or "загрузить шаблон" in lt or b.text().strip() == "Печать":
            b.setMaximumHeight(28)
            b.setStyleSheet("QPushButton{padding:3px 10px;font-size:12px;border-radius:4px;}")
    self.tbl_tpl.setMaximumHeight(150)
    self.tbl_tpl.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
    self.table.setMinimumHeight(170)
    self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

_w19_orig_init = DocumentsTab.__init__
def _w19_init(self, *a, **kw):
    _w19_orig_init(self, *a, **kw)
    try:
        _w19_apply(self)
    except Exception as e:
        print("W19:", e)
DocumentsTab.__init__ = _w19_init

# === W20_FIX_LAYOUT: скроллы на списках, нижние кнопки — компактный ряд ===
def _w20_apply(self):
    from PyQt6.QtWidgets import QHBoxLayout
    from PyQt6.QtCore import Qt
    # 1. фиксированные высоты + скролл всегда
    self.tbl_tpl.setFixedHeight(140)
    self.tbl_tpl.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    self.table.setFixedHeight(190)
    self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    # 2. собрать нижние кнопки в один компактный горизонтальный ряд
    btns = []
    for b in self.findChildren(QPushButton):
        lt = b.text().strip().lower()
        if ("создать шаблон" in lt) or ("загрузить шаблон" in lt) or lt == "печать":
            btns.append(b)
    if btns and not getattr(self, "_w20_done", False):
        self._w20_done = True
        row = QHBoxLayout()
        row.addStretch(1)
        for b in btns:
            b.setFixedHeight(26)
            b.setMinimumWidth(140)
            b.setMaximumWidth(200)
            b.setStyleSheet("QPushButton{padding:2px 10px;font-size:12px;border-radius:4px;}")
            row.addWidget(b)
        row.addStretch(1)
        self.layout().addLayout(row)

_w20_orig_init = DocumentsTab.__init__
def _w20_init(self, *a, **kw):
    _w20_orig_init(self, *a, **kw)
    try:
        _w20_apply(self)
    except Exception as e:
        print("W20:", e)
DocumentsTab.__init__ = _w20_init