# -*- coding: utf-8 -*-
"""Face ID v2 — карточка клиента с фото: поиск, регистрация шаблона, список шаблонов."""
import base64
import json
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QSplitter, QGroupBox, QFormLayout)
from PyQt6.QtGui import QPixmap, QFont
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
        self._clients = []
        self._current = None
        self.setStyleSheet(_t("widget_style"))
        root = QHBoxLayout(self)

        split = QSplitter(Qt.Orientation.Horizontal)

        # ---------- левая колонка: клиент ----------
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 8, 8, 8)

        search = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("ФИО, телефон или ID клиента…")
        self.ed_search.returnPressed.connect(self.search_client)
        search.addWidget(self.ed_search, 1)
        b = QPushButton("Найти")
        b.clicked.connect(self.search_client)
        search.addWidget(b)
        lv.addLayout(search)

        self.card = QGroupBox("Клиент не выбран")
        form = QFormLayout(self.card)
        self.lbl_fio = QLabel("—")
        self.lbl_phone = QLabel("—")
        self.lbl_sub = QLabel("—")
        self.lbl_photo = QLabel("фото не загружено")
        self.lbl_photo.setFixedSize(180, 180)
        self.lbl_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo.setStyleSheet("border: 1px dashed #475569; color: #64748b;")
        form.addRow("ФИО:", self.lbl_fio)
        form.addRow("Телефон:", self.lbl_phone)
        form.addRow("Абонемент:", self.lbl_sub)
        form.addRow("Фото:", self.lbl_photo)
        lv.addWidget(self.card)

        row = QHBoxLayout()
        b_load = QPushButton("📂 Загрузить фото и зарегистрировать")
        b_load.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_load.clicked.connect(self.register_photo)
        row.addWidget(b_load)
        lv.addLayout(row)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(150)
        self.details.setPlaceholderText("Результат регистрации / verify…")
        lv.addWidget(self.details)
        lv.addStretch(1)
        split.addWidget(left)

        # ---------- правая колонка: шаблоны ----------
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 8, 8, 8)
        rv.addWidget(QLabel("<b>Шаблоны Face ID</b>"))
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["ID", "Клиент ID", "Создан", "Качество"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setStyleSheet(_t("table_style"))
        rv.addWidget(self.tbl, 1)

        bar = QHBoxLayout()
        b_ref = QPushButton("Обновить список")
        b_ref.clicked.connect(self.load_templates)
        bar.addWidget(b_ref)
        b_eng = QPushButton("Движок Face ID")
        b_eng.clicked.connect(self.engine_info)
        bar.addWidget(b_eng)
        b_sim = QPushButton("▶ Симуляция: verify")
        b_sim.clicked.connect(self.sim_verify)
        bar.addWidget(b_sim)
        bar.addStretch(1)
        rv.addLayout(bar)
        split.addWidget(right)

        split.setSizes([460, 620])
        root.addWidget(split)

        self.load_templates()
        self._run(self.api.get_clients, self._fill_clients)

    # ---------- infra ----------
    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda m: self._show("Ошибка: %s" % m, ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.details.setPlainText(str(msg))

    # ---------- клиент ----------
    def _fill_clients(self, data):
        self._clients = data if isinstance(data, list) else []

    def search_client(self):
        q = self.ed_search.text().strip().lower()
        if len(q) < 2:
            QMessageBox.information(self, "Поиск", "Введите минимум 2 символа")
            return
        for c in self._clients:
            fio = " ".join(str(c.get(k) or "") for k in
                           ("last_name", "first_name", "middle_name")).strip()
            if q in fio.lower() or q in str(c.get("phone") or "").lower() \
               or q in str(c.get("id") or "").lower():
                self._select(c)
                return
        self._show("Клиент не найден: %s" % q, ok=False)

    def _select(self, c):
        self._current = c
        fio = " ".join(x for x in (c.get("last_name"), c.get("first_name"),
                                   c.get("middle_name")) if x) or "—"
        self.card.setTitle("👤 %s" % fio)
        self.lbl_fio.setText(fio)
        self.lbl_phone.setText(str(c.get("phone") or "—"))
        self._run(self.api.get_subscriptions, self._fill_subs)

    def _fill_subs(self, subs):
        if not self._current:
            return
        cid = str(self._current.get("id"))
        mine = [s for s in (subs if isinstance(subs, list) else [])
                if str(s.get("client_id")) == cid]
        if not mine:
            self.lbl_sub.setText("нет абонемента")
            return
        s = sorted(mine, key=lambda x: str(x.get("end_date") or ""), reverse=True)[0]
        self.lbl_sub.setText("%s (до %s)" % (s.get("status"), s.get("end_date")))

    # ---------- фото / регистрация ----------
    def register_photo(self):
        if not self._current:
            QMessageBox.information(self, "Face ID", "Сначала найдите и выберите клиента")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Фото клиента", "", "Изображения (*.jpg *.jpeg *.png *.bmp)")
        if not path:
            return
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            QMessageBox.critical(self, "Фото", str(e))
            return
        self.lbl_photo.setPixmap(QPixmap(path).scaled(
            180, 180, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        cid = str(self._current.get("id"))
        self._run(lambda: self.api.face_register(cid, b64), self._on_registered)

    def _on_registered(self, r):
        try:
            self.details.setPlainText(json.dumps(r, ensure_ascii=False, indent=2, default=str)[:1500])
        except Exception:
            self.details.setPlainText(str(r))
        ok = False
        if isinstance(r, dict):
            ok = bool(r.get("ok") or r.get("success") or r.get("id")
                      or r.get("template_id") or r.get("template"))
        if ok:
            self._show("✅ Шаблон зарегистрирован:\n" + self.details.toPlainText())
            self.load_templates()
        else:
            self._show("⚠️ Ответ сервера (проверьте):\n" + self.details.toPlainText())

    # ---------- шаблоны ----------
    def load_templates(self):
        self._run(self.api.face_templates, self._fill_templates)

    def _fill_templates(self, rows):
        rows = rows if isinstance(rows, list) else []
        self.tbl.setRowCount(0)
        for t in rows:
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)
            vals = [str(t.get("id") or t.get("template_id") or "")[:12],
                    str(t.get("client_id") or t.get("user_id") or "")[:12],
                    str(t.get("created_at") or "")[:19],
                    str(t.get("quality_score") or t.get("quality") or "")]
            for j, v in enumerate(vals):
                self.tbl.setItem(i, j, QTableWidgetItem(v))
        self._show("Шаблонов: %d" % len(rows))

    # ---------- сервис ----------
    def engine_info(self):
        self._run(self.api.face_engine_info,
                  lambda r: self._show(json.dumps(r, ensure_ascii=False, indent=2, default=str)[:1200]))

    def sim_verify(self):
        self._run(lambda: self.api.verify_face(TEST_PHOTO), self._on_verify)

    def _on_verify(self, res):
        ok = isinstance(res, dict) and any(
            res.get(k) is True for k in ("verified", "access_granted", "match", "success", "allowed"))
        txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)[:1200]
        self._show(("✅ Доступ РАЗРЕШЁН\n" if ok else "⛔ Отказ / нет совпадения\n") + txt, ok=ok)


FaceIDTab = FaceIdTab  # алиас для совместимости с main_window