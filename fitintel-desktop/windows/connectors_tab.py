# -*- coding: utf-8 -*-
"""E59 UI: коннекторы внешних клубных систем (1С:Фитнес клуб / CRM «ХИТ»)."""
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QPlainTextEdit)
from PyQt6.QtCore import QThread, pyqtSignal
from .form_dialog import FormDialog

TYPE_LABELS = {"fitness1c": "1С:Фитнес клуб", "hit": "CRM «ХИТ» (B-Office)"}


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
            self.fail.emit(str(e)[:300])


class ConnectorsTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._workers = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        bar = QHBoxLayout()
        b_add = QPushButton("＋ Добавить подключение")
        b_add.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_add.clicked.connect(self._add)
        bar.addWidget(b_add)
        b_del = QPushButton("Удалить")
        b_del.setStyleSheet("QPushButton { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_del.clicked.connect(self._delete)
        bar.addWidget(b_del)
        b_test = QPushButton("🔌 Тест связи")
        b_test.clicked.connect(self._test)
        bar.addWidget(b_test)
        b_sync = QPushButton("🔄 Синхронизировать")
        b_sync.setStyleSheet("QPushButton { background: #2563eb; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_sync.clicked.connect(self._sync)
        bar.addWidget(b_sync)
        b_log = QPushButton("📋 Журнал")
        b_log.clicked.connect(self._log)
        bar.addWidget(b_log)
        b_ref = QPushButton("Обновить")
        b_ref.clicked.connect(self.refresh)
        bar.addWidget(b_ref)
        bar.addStretch(1)
        lay.addLayout(bar)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Название", "Тип", "Адрес", "Последний синхрон", "Статус"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.tbl, 1)

        hint = QLabel("Синхронизация односторонняя: данные приезжают из внешней системы "
                      "(клиенты → абонементы → визиты) без дублей. 1С остаётся учётной системой.")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.refresh()

    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda m: QMessageBox.warning(self, "Коннекторы", m))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _base(self):
        return self.api._url("/connectors")

    def refresh(self):
        self._run(lambda: self.api.session.get(self._base(), timeout=30).json(),
                  self._fill)

    def _fill(self, data):
        rows = data.get("connectors", []) if isinstance(data, dict) else []
        self.tbl.setRowCount(len(rows))
        for i, c in enumerate(rows):
            self.tbl.setItem(i, 0, QTableWidgetItem(str(c.get("name"))))
            self.tbl.setItem(i, 1, QTableWidgetItem(TYPE_LABELS.get(c.get("type"), c.get("type"))))
            self.tbl.setItem(i, 2, QTableWidgetItem(str(c.get("base_url"))))
            self.tbl.setItem(i, 3, QTableWidgetItem(str(c.get("last_sync_at") or "—")[:19]))
            st = str(c.get("last_status") or "—")
            self.tbl.setItem(i, 4, QTableWidgetItem(st + (": " + str(c.get("last_message"))[:60] if c.get("last_message") else "")))
            self.tbl.item(i, 0).setData(33, str(c.get("id")))

    def _cid(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Коннекторы", "Выберите подключение в таблице")
            return None
        return self.tbl.item(row, 0).data(33)

    def _add(self):
        dlg = FormDialog("Новое подключение", [
            ("name", "Название *"),
            ("type", "Тип *", "combo", [("1С:Фитнес клуб (API V3)", "fitness1c"),
                                        ("CRM «ХИТ» (B-Office)", "hit")]),
            ("base_url", "Адрес API * (http://...)"),
            ("auth_login", "Логин API"),
            ("auth_password", "Пароль API"),
        ], self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["name"] or not v["base_url"]:
            QMessageBox.warning(self, "Коннекторы", "Название и адрес обязательны")
            return
        def _create():
            r = self.api.session.post(self._base(), json=v, timeout=30)
            r.raise_for_status()
            return r.json()
        self._run(_create, lambda _r: (QMessageBox.information(self, "Коннекторы", "Подключение создано"), self.refresh()))

    def _delete(self):
        cid = self._cid()
        if not cid:
            return
        if QMessageBox.question(self, "Удаление", "Удалить выбранное подключение?") != QMessageBox.StandardButton.Yes:
            return
        self._run(lambda: (self.api.session.delete(self._base() + "/" + cid, timeout=30),
                           self.refresh()),
                  lambda _r: None)

    def _test(self):
        cid = self._cid()
        if cid:
            self._run(lambda: self.api.session.post(self._base() + f"/{cid}/test", timeout=60).json(),
                      lambda r: QMessageBox.information(self, "Тест связи", json.dumps(r, ensure_ascii=False, indent=2)[:500]))

    def _sync(self):
        cid = self._cid()
        if not cid:
            return
        def _do():
            r = self.api.session.post(self._base() + f"/{cid}/sync", timeout=300)
            r.raise_for_status()
            return r.json()
        def _show(r):
            lines = []
            for x in r.get("results", []):
                if x.get("status") == "success":
                    lines.append(f"✅ {x['entity']}: создано {x.get('created',0)}, обновлено {x.get('updated',0)}, пропущено {x.get('skipped',0)}")
                else:
                    lines.append(f"❌ {x['entity']}: {x.get('message','')[:150]}")
            QMessageBox.information(self, "Синхронизация", "\n".join(lines) or "Нет результатов")
            self.refresh()
        self._run(_do, _show)

    def _log(self):
        cid = self._cid()
        if cid:
            self._run(lambda: self.api.session.get(self._base() + f"/{cid}/log", timeout=30).json(),
                      self._show_log)

    def _show_log(self, data):
        d = QDialog(self)
        d.setWindowTitle("Журнал синхронизации")
        d.resize(640, 420)
        v = QVBoxLayout(d)
        txt = QPlainTextEdit()
        txt.setReadOnly(True)
        rows = data.get("entries", []) if isinstance(data, dict) else []
        txt.setPlainText("\n".join(f"{e.get('at','')[:19]}  {e.get('entity',''):15s} "
                                   f"{e.get('records',0):4d}  {e.get('status',''):8s} {e.get('message','')}"
                                   for e in rows) or "Журнал пуст")
        v.addWidget(txt)
        b = QPushButton("Закрыть")
        b.clicked.connect(d.accept)
        v.addWidget(b)
        d.exec()