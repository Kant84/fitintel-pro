# -*- coding: utf-8 -*-
"""Face ID: проверка движка, список шаблонов, симуляция verify (фото b64)."""
import json
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView)
from . import theme

TEST_PHOTO = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
              "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")

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

class FaceIdTab(QWidget):
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

        info = QLabel("verify ждёт фото в base64. Симуляция шлёт тестовое фото 1x1; "
                      "в реальной работе фото приходит с камеры терминала.")
        info.setWordWrap(True)
        v.addWidget(info)

        bar = QHBoxLayout()
        for text, slot in [("Движок Face ID", self.engine_info),
                           ("Шаблоны (список)", self.load_templates),
                           ("Симуляция: verify", self.sim_verify),
                           ("Симуляция: Разрешить доступ", self.sim_allow),
                           ("Симуляция: Запретить доступ", self.sim_deny)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        v.addLayout(bar)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(180)
        v.addWidget(self.details)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["ID шаблона", "Клиент", "Создан"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setStyleSheet(_t("table_style"))
        v.addWidget(self.tbl, 1)

    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda msg: self._show("Ошибка API: %s" % msg, ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w)
                           if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.banner.setText(str(msg))
        self.banner.setStyleSheet(_t("banner_style", ok))
        self.banner.show()

    def _dump(self, obj):
        try:
            self.details.setPlainText(json.dumps(obj, ensure_ascii=False,
                                                 indent=2, default=str))
        except Exception:
            self.details.setPlainText(str(obj))

    def engine_info(self):
        self._run(self.api.face_engine_info,
                  lambda r: (self._dump(r), self._show("Движок: OK")))

    def load_templates(self):
        def _fill(rows):
            rows = rows if isinstance(rows, list) else []
            self.tbl.setRowCount(0)
            for t in rows:
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)
                vals = [str(t.get("id") or t.get("template_id") or "")[:12],
                        str(t.get("client_id") or ""),
                        str(t.get("created_at") or "")[:19]]
                for j, val in enumerate(vals):
                    self.tbl.setItem(r, j, QTableWidgetItem(val))
            self._show("Шаблонов: %d" % len(rows))
        self._run(self.api.face_templates, _fill)

    def _verdict(self, res):
        self._dump(res)
        ok = False
        if isinstance(res, dict):
            for k in ("verified", "access_granted", "match", "success", "allowed"):
                if res.get(k) is True:
                    ok = True
                    break
        self._show("Доступ РАЗРЕШЁН" if ok else
                   "Отказ (сервер не подтвердил лицо — см. ответ ниже)", ok=ok)

    def sim_verify(self):
        self._run(lambda: self.api.verify_face(TEST_PHOTO), self._verdict)

    def sim_allow(self):
        self._run(lambda: self.api.verify_face(TEST_PHOTO), self._verdict)

    def sim_deny(self):
        self._run(lambda: self.api.verify_face("not_a_real_photo"),
                  self._verdict)
FaceIDTab = FaceIdTab  # алиас для совместимости с main_window
