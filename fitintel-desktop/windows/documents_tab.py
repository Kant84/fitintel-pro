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

# === ГОТОВЫЕ ШАБЛОНЫ: договоры и документы (генерация + скачивание) ===
try:
    import datetime as _dt
    import html as _html
    from PyQt6.QtWidgets import (QGroupBox, QComboBox, QTextEdit, QLabel, QPushButton,
                                 QGridLayout, QHBoxLayout, QMessageBox)
    from PyQt6.QtCore import QThread as _QTh, pyqtSignal as _psig

    _TEMPLATES = {
        "Договор оказания фитнес-услуг": (
            "ДОГОВОР № ___\nоказания фитнес-услуг\n\n"
            "г. {{city}}                                        «{{day}}» {{month}} {{year}} г.\n\n"
            "{{club_name}}, именуемый в дальнейшем «Исполнитель», в лице директора, действующего на основании Устава, "
            "с одной стороны, и {{client_name}}, именуемый(ая) в дальнейшем «Клиент», с другой стороны, "
            "заключили настоящий Договор о нижеследующем:\n\n"
            "1. ПРЕДМЕТ ДОГОВОРА\n"
            "1.1. Исполнитель обязуется оказать Клиенту фитнес-услуги (тренажёрный зал, групповые программы, бассейн, сауна), "
            "а Клиент обязуется принять и оплатить их.\n"
            "1.2. Перечень услуг, сроки и стоимость определяются выбранным Клиентом тарифом (абонементом).\n\n"
            "2. ПОРЯДОК РАСЧЁТОВ\n"
            "2.1. Оплата производится Клиентом авансом в размере 100% стоимости тарифа.\n"
            "2.2. Обязательство по оплате считается исполненным с момента зачисления средств на расчётный счёт Исполнителя "
            "или внесения наличных в кассу с выдачей кассового чека.\n\n"
            "3. ОТВЕТСТВЕННОСТЬ СТОРОН\n"
            "3.1. Исполнитель не несёт ответственности за травмы, возникшие при нарушении Клиентом правил техники безопасности "
            "и противопоказаний к занятиям.\n\n"
            "4. РЕКВИЗИТЫ И ПОДПИСИ СТОРОН\n\n"
            "Клиент: {{client_name}}\nТелефон: {{phone}}\nEmail: {{email}}\n\n"
            "Исполнитель: {{club_name}}\n\n"
            "Подписи сторон: ______________ / ______________"
        ),
        "Согласие на обработку персональных данных": (
            "СОГЛАСИЕ\nна обработку персональных данных\n\n"
            "Я, {{client_name}}, телефон {{phone}}, email {{email}},\n"
            "в соответствии с Федеральным законом № 152-ФЗ «О персональных данных» даю согласие "
            "{{club_name}} (далее — Оператор) на обработку моих персональных данных: ФИО, дата рождения, "
            "контактные данные, фотографии (в т.ч. биометрические шаблоны для системы Face ID), сведения о посещениях "
            "и платежах.\n\n"
            "Цели обработки: оказание фитнес-услуг, идентификация при входе, информирование об акциях и изменениях "
            "расписания, исполнение обязанностей по 54-ФЗ и 152-ФЗ.\n\n"
            "Согласие действует с даты подписания и до его отзыва. Отзыв оформляется письменным заявлением.\n\n"
            "Дата: {{date}}\nПодпись: ______________ / {{client_name}}"
        ),
        "Договор купли-продажи абонемента": (
            "ДОГОВОР № ___\nкупли-продажи абонемента\n\n"
            "г. {{city}}                                        «{{day}}» {{month}} {{year}} г.\n\n"
            "{{club_name}} (Продавец) и {{client_name}} (Покупатель) заключили договор:\n\n"
            "1. Предмет: Продавец передаёт, Покупатель принимает и оплачивает абонемент "
            "(тариф: ____________, срок действия: ____________).\n"
            "2. Стоимость абонемента: ____________ руб. Оплата произведена в полном объёме.\n"
            "3. Абонемент даёт право посещения согласно правилам клуба и ограничениям тарифа.\n"
            "4. Возврат неиспользованного абонемента — по правилам клуба и законодательству РФ.\n\n"
            "Дата: {{date}}\nПродавец: ______________    Покупатель: ______________ / {{client_name}}"
        ),
        "Справка о количестве посещений": (
            "СПРАВКА\n\n"
            "Выдана {{client_name}} в том, что за период ____________ по ____________ "
            "клиент посетил {{club_name}} ______ раз(а).\n\n"
            "Телефон клиента: {{phone}}\n\n"
            "Дата выдачи: {{date}}\n"
            "Подпись администратора: ______________\nМ.П."
        ),
    }

    class _TplClientsLoader(_QTh):
        done = _psig(list)
        def __init__(self, api):
            super().__init__()
            self.api = api
        def run(self):
            try:
                self.done.emit(self.api.get_clients() or [])
            except Exception:
                self.done.emit([])

    def _render_template(tpl, client):
        now = _dt.datetime.now()
        name = "____________"
        phone = "____________"
        email = "—"
        if client:
            name = " ".join(x for x in (client.get("last_name"), client.get("first_name"), client.get("middle_name")) if x) or name
            phone = client.get("phone") or phone
            email = client.get("email") or email
        vals = {"client_name": name, "phone": phone, "email": email,
                "day": str(now.day), "month": now.strftime("%B"), "year": str(now.year),
                "date": now.strftime("%d.%m.%Y"), "city": "Москва", "club_name": "Фитнес-клуб"}
        out = tpl
        for k, v in vals.items():
            out = out.replace("{{%s}}" % k, str(v))
        return out

    def _tpl_save_pdf(parent, title, text):
        from paths import ASSETS, APP_DIR
        p = ASSETS / "DejaVuSans.ttf"
        if not p.exists():
            QMessageBox.warning(parent, "PDF", "Не найден assets/DejaVuSans.ttf")
            return
        from PyQt6.QtWidgets import QFileDialog
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont("DejaVu", str(p)))
        d = APP_DIR / "export"
        d.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(parent, "Сохранить PDF", str(d / (title[:60] + ".pdf")), "PDF (*.pdf)")
        if not path:
            return
        style = ParagraphStyle("t", fontName="DejaVu", fontSize=10, leading=14)
        story = []
        for line in text.split("\n"):
            story.append(Paragraph(_html.escape(line).replace(" ", "&nbsp;") or "&nbsp;", style))
            story.append(Spacer(1, 2 * mm))
        SimpleDocTemplate(path, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                          topMargin=20*mm, bottomMargin=20*mm).build(story)
        QMessageBox.information(parent, "Готово", f"Сохранено: {path}")

    def _tpl_save_html(parent, title, text):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from paths import APP_DIR
        d = APP_DIR / "export"
        d.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(parent, "Сохранить HTML", str(d / (title[:60] + ".html")), "HTML (*.html)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("<html><head><meta charset='utf-8'><title>%s</title></head><body><pre>%s</pre></body></html>"
                     % (_html.escape(title), _html.escape(text)))
        QMessageBox.information(parent, "Готово", f"Сохранено: {path}")

    def _tpl_save_xlsx_json(parent, title, text, fmt):
        from windows.export_helper import export_table_xlsx, _write_json
        rows = [[ln] for ln in text.split("\n")]
        if fmt == "xlsx":
            export_table_xlsx(parent, ["Документ"], rows, title[:40], title)
        else:
            _write_json(parent, ["Документ"], rows, title[:40])

    def _fill_tpl_clients(self, clients):
        for c in clients:
            nm = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x) or str(c.get("id"))[:8]
            self._tpl_client.addItem(nm, c)

    _orig_docs_init = DocumentsTab.__init__
    def _docs_init(self, api, *a, **kw):
        _orig_docs_init(self, api, *a, **kw)
        try:
            gb = QGroupBox("Готовые шаблоны (договоры и документы)")
            grid = QGridLayout(gb)
            self._tpl_combo = QComboBox()
            self._tpl_combo.addItems(sorted(_TEMPLATES.keys()))
            self._tpl_client = QComboBox()
            self._tpl_client.addItem("— без клиента —", None)
            self._tpl_preview = QTextEdit()
            self._tpl_preview.setReadOnly(True)
            self._tpl_preview.setMinimumHeight(230)
            b_gen = QPushButton(" Сформировать")
            b_gen.setStyleSheet("background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600;")
            grid.addWidget(QLabel("Шаблон:"), 0, 0)
            grid.addWidget(self._tpl_combo, 0, 1)
            grid.addWidget(QLabel("Клиент:"), 0, 2)
            grid.addWidget(self._tpl_client, 0, 3)
            grid.addWidget(b_gen, 0, 4)
            grid.addWidget(self._tpl_preview, 1, 0, 1, 5)
            hb = QHBoxLayout()
            hb.addStretch()
            for fmt, label in [("pdf", "PDF"), ("html", "HTML"), ("xlsx", "XLSX"), ("json", "JSON")]:
                b = QPushButton(label)
                b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; font-weight: 600; }")
                b.clicked.connect(lambda _, f=fmt: _dl(f))
                hb.addWidget(b)
            grid.addLayout(hb, 2, 0, 1, 5)
            self.layout().addWidget(gb)

            def _gen():
                self._tpl_preview.setPlainText(
                    _render_template(_TEMPLATES[self._tpl_combo.currentText()], self._tpl_client.currentData()))
            b_gen.clicked.connect(_gen)

            def _dl(fmt):
                text = self._tpl_preview.toPlainText()
                if not text.strip():
                    QMessageBox.information(self, "Шаблоны", "Сначала нажмите «Сформировать»")
                    return
                title = self._tpl_combo.currentText()
                if fmt == "pdf":
                    _tpl_save_pdf(self, title, text)
                elif fmt == "html":
                    _tpl_save_html(self, title, text)
                else:
                    _tpl_save_xlsx_json(self, title, text, fmt)

            DocumentsTab._fill_tpl_clients = _fill_tpl_clients
            _ld = _TplClientsLoader(api)
            _ld.done.connect(self._fill_tpl_clients)
            _ld.start()
        except Exception as _e:
            print("templates block:", _e)
    DocumentsTab.__init__ = _docs_init
    print("DOC TEMPLATES OK: documents_tab.py")
except Exception as _e:
    print("DOC TEMPLATES FAIL:", _e)