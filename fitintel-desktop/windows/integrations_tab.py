# -*- coding: utf-8 -*-
"""E56: вкладка «Интеграции» — API-ключи 1С, Mobifitness, MAX, ЮKassa."""
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit)
from . import theme
from .form_dialog import FormDialog

def _t(name, *args):
    f = getattr(theme, name, None)
    if not callable(f):
        return ""
    for a in (args, ()):
        try:
            return f(*a)
        except TypeError:
            continue
        except Exception:
            return ""
    return ""

class Worker(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(str)
    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(str(e))

class IntegrationsTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._workers = []
        self._schema = {}
        self._items = []
        self.setStyleSheet(_t("widget_style"))
        v = QVBoxLayout(self)
        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.hide()
        v.addWidget(self.banner)
        bar = QHBoxLayout()
        for text, slot in [("Обновить", self.load_all),
                           ("⚙ Настроить", self.configure),
                           ("⚡ Проверить подключение", self.test)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        v.addLayout(bar)
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Код", "Система", "Статус", "Обновлено"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setStyleSheet(_t("table_style"))
        self.tbl.doubleClicked.connect(lambda _i: self.configure())
        v.addWidget(self.tbl, 1)
        self.load_all()

    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda m: self._show(m, ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.banner.setText(str(msg))
        self.banner.setStyleSheet(_t("banner_style", ok))
        self.banner.show()

    def load_all(self):
        self._run(self.api.get_integration_schema, self._got_schema)

    def _got_schema(self, schema):
        self._schema = schema if isinstance(schema, dict) else {}
        self._run(self.api.get_integrations, self._fill)

    def _fill(self, data):
        items = data.get("items", data) if isinstance(data, dict) else data
        self._items = items if isinstance(items, list) else []
        self.tbl.setRowCount(0)
        for it in self._items:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            status = "✅ настроено" if it.get("configured") else "— не настроено"
            vals = [it.get("service", ""), it.get("title", ""), status,
                    str(it.get("updated_at") or "")[:19]]
            for j, val in enumerate(vals):
                cell = QTableWidgetItem(str(val))
                if j == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, it.get("service"))
                self.tbl.setItem(r, j, cell)
        self._show("Интеграций: %d" % len(self._items))

    def _service(self):
        r = self.tbl.currentRow()
        if r < 0:
            self._show("Выбери интеграцию в таблице.", ok=False)
            return None
        return self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole)

    def configure(self):
        svc = self._service()
        if not svc:
            return
        meta = self._schema.get(svc, {})
        fields = meta.get("fields", [])
        cur = {}
        for it in self._items:
            if it.get("service") == svc:
                cur = it.get("config") or {}
        dlg = FormDialog([(f["key"], f["label"], "text", None) for f in fields], self)
        dlg.setWindowTitle("Настройка: " + meta.get("title", svc) +
                           "  (оставь *** — секрет не изменится)")
        try:
            edits = dlg.findChildren(QLineEdit)
            for ed, f in zip(edits, fields):
                ed.setText(str(cur.get(f["key"], "***" if f.get("secret") else "")))
        except Exception:
            pass
        if not dlg.exec():
            return
        self._run(lambda: self.api.save_integration(svc, dlg.values()),
                  lambda _r: (self._show("Сохранено: %s" % svc), self.load_all()))

    def test(self):
        svc = self._service()
        if not svc:
            return
        def _done(res):
            ok = isinstance(res, dict) and res.get("ok")
            detail = res.get("detail", "") if isinstance(res, dict) else res
            self._show(("✅ Подключение OK. " if ok else "❌ Ошибка: ") + str(detail), ok=bool(ok))
        self._run(lambda: self.api.test_integration(svc), _done)
