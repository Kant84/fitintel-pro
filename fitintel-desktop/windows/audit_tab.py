# -*- coding: utf-8 -*-
"""E71: Экран «История» — журнал аудита (кто/когда/что изменил)."""
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit)
from PyQt6.QtCore import QThread, pyqtSignal, QDate

from . import theme
from .form_dialog import FormDialog


class AuditWorker(QThread):
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


class AuditTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._workers = []
        self.setStyleSheet(_t("widget_style"))
        v = QVBoxLayout(self)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.hide()
        v.addWidget(self.banner)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Сущность:"))
        self.cmb_entity = QComboBox()
        self.cmb_entity.addItem("Все", None)
        for code, label in [("user", "Пользователи"), ("client", "Клиенты"),
                            ("payment", "Платежи"), ("subscription", "Абонементы"),
                            ("visit", "Визиты"), ("role", "Роли")]:
            self.cmb_entity.addItem(label, code)
        bar.addWidget(self.cmb_entity)
        bar.addWidget(QLabel("Действие:"))
        self.cmb_action = QComboBox()
        self.cmb_action.addItem("Все", None)
        for code, label in [("created", "Создано"), ("updated", "Изменено"),
                            ("deleted", "Удалено")]:
            self.cmb_action.addItem(label, code)
        bar.addWidget(self.cmb_action)
        bar.addWidget(QLabel("Кто:"))
        self.ed_actor = QLineEdit()
        self.ed_actor.setPlaceholderText("логин")
        self.ed_actor.setMaximumWidth(130)
        bar.addWidget(self.ed_actor)
        self.dt_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd")
        bar.addWidget(self.dt_from)
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd")
        bar.addWidget(self.dt_to)
        b_load = QPushButton("Загрузить")
        b_load.clicked.connect(self.load)
        bar.addWidget(b_load)
        b_ret = QPushButton("Срок хранения…")
        b_ret.clicked.connect(self.retention_dialog)
        bar.addWidget(b_ret)
        bar.addStretch(1)
        v.addLayout(bar)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(
            ["Когда", "Кто", "Действие", "Сущность", "ID", "Детали"])
        self.tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setStyleSheet(_t("table_style"))
        v.addWidget(self.tbl, 1)
        self.load()

    def _run(self, fn, cb):
        w = AuditWorker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda m: self._show(m, ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.banner.setText(str(msg))
        self.banner.setStyleSheet(_t("banner_style", ok))
        self.banner.show()

    def load(self):
        params = {
            "limit": 500,
            "date_from": self.dt_from.date().toString("yyyy-MM-dd"),
            "date_to": self.dt_to.date().toString("yyyy-MM-dd"),
        }
        if self.cmb_entity.currentData():
            params["entity"] = self.cmb_entity.currentData()
        if self.cmb_action.currentData():
            params["action"] = self.cmb_action.currentData()
        if self.ed_actor.text().strip():
            params["actor"] = self.ed_actor.text().strip()
        self._run(lambda: self.api.session.get(
            self.api._url("/audit"), params=params).json(), self._fill)

    def _fill(self, data):
        rows = data.get("entries", []) if isinstance(data, dict) else []
        self.tbl.setRowCount(len(rows))
        for i, e in enumerate(rows):
            self.tbl.setItem(i, 0, QTableWidgetItem(str(e.get("at") or "")))
            self.tbl.setItem(i, 1, QTableWidgetItem(str(e.get("actor") or "")))
            self.tbl.setItem(i, 2, QTableWidgetItem(str(e.get("action") or "")))
            self.tbl.setItem(i, 3, QTableWidgetItem(str(e.get("entity_type") or "")))
            self.tbl.setItem(i, 4, QTableWidgetItem(str(e.get("entity_id") or "")[:8]))
            detail = str(e.get("message") or "")
            diff = e.get("after_data") or e.get("before_data")
            if diff:
                detail += " | " + json.dumps(diff, ensure_ascii=False, default=str)[:140]
            self.tbl.setItem(i, 5, QTableWidgetItem(detail))
        self._show(f"Записей: {len(rows)}")

    def retention_dialog(self):
        self._run(lambda: self.api.session.get(
            self.api._url("/audit/retention")).json(), self._ret_show)

    def _ret_show(self, data):
        labels = [("Месяц", 30), ("Полгода", 180), ("Год", 365),
                  ("2 года", 730), ("Бессрочно", 0)]
        cur = int(data.get("days", 365))
        dlg = FormDialog("Срок хранения истории",
                         [("period", "Хранить историю", "combo",
                           [(f"{n} ({d} дн.)", d) for n, d in labels])], self)
        dlg._widgets["period"][1].setCurrentIndex(
            next((i for i, (_, d) in enumerate(labels) if d == cur), 2))
        if not dlg.exec():
            return
        days = dlg.values()["period"]
        self._run(lambda: self.api.session.post(
            self.api._url("/audit/retention"), json={"days": days}).json(),
            lambda r: (self._show(f"Срок хранения: {r.get('days')} дн."), self.load()))