# -*- coding: utf-8 -*-
"""Face ID v3 — карточка клиента с фото: поиск, съёмка с камеры/загрузка,
регистрация шаблона, список шаблонов, настройки движка (вкл. хранение фото)."""
import base64
import json
import os
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QSplitter, QGroupBox, QFormLayout,
    QDialog, QInputDialog)
from PyQt6.QtGui import QPixmap, QImage
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


class CameraDialog(QDialog):
    """Предпросмотр веб-камеры + съёмка кадра."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(" Съёмка фото — FitIntel Face ID")
        self.resize(680, 560)
        self.photo_path = None
        self._frame = None
        self.cap = None

        v = QVBoxLayout(self)
        self.lbl = QLabel("Запуск камеры…")
        self.lbl.setMinimumSize(640, 480)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setStyleSheet("background: #0f172a; color: #94a3b8;")
        v.addWidget(self.lbl, 1)

        bar = QHBoxLayout()
        self.b_shot = QPushButton(" Снять")
        self.b_shot.setEnabled(False)
        self.b_shot.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 10px 28px; font-weight: 700; }")
        self.b_shot.clicked.connect(self._shot)
        bar.addStretch(1)
        bar.addWidget(self.b_shot)
        b_cancel = QPushButton("Отмена")
        b_cancel.clicked.connect(self.reject)
        bar.addWidget(b_cancel)
        bar.addStretch(1)
        v.addLayout(bar)

        try:
            import cv2
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0)
        except Exception:
            self.cap = None
        if not self.cap or not self.cap.isOpened():
            self.lbl.setText("Камера не найдена.\nПроверьте подключение и что камера не занята другим приложением.")
            return
        self.b_shot.setEnabled(True)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(40)

    def _update(self):
        import cv2
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return
        self._frame = frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.lbl.setPixmap(QPixmap.fromImage(img).scaled(
            self.lbl.width(), self.lbl.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def _shot(self):
        import cv2
        if self._frame is None:
            return
        self.photo_path = os.path.join(tempfile.gettempdir(), "fitintel_face.jpg")
        cv2.imwrite(self.photo_path, self._frame)
        self.accept()

    def closeEvent(self, ev):
        try:
            self._timer.stop()
        except Exception:
            pass
        if self.cap is not None:
            self.cap.release()
        super().closeEvent(ev)


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
        b_cam = QPushButton(" Снять с камеры")
        b_cam.setStyleSheet("QPushButton { background: #2563eb; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_cam.clicked.connect(self.capture_from_camera)
        row.addWidget(b_cam)
        b_load = QPushButton(" Загрузить файл")
        b_load.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_load.clicked.connect(self.register_photo)
        row.addWidget(b_load)
        lv.addLayout(row)
        b_me = QPushButton(" Проверить меня")
        b_me.setStyleSheet("QPushButton { background: #7c3aed; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_me.clicked.connect(self.verify_me)
        
        row.addWidget(b_me)
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
        b_del = QPushButton(" Удалить шаблон")
        b_del.clicked.connect(self.delete_template)
        bar.addWidget(b_del)
        b_set = QPushButton("Настройки движка…")
        b_set.clicked.connect(self.engine_settings)
        bar.addWidget(b_set)
        b_eng = QPushButton("Движок Face ID")
        b_eng.clicked.connect(self.engine_info)
        bar.addWidget(b_eng)
        b_sim = QPushButton(" Симуляция: verify")
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
        self.card.setTitle(" %s" % fio)
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

    # ---------- фото: камера / файл ----------
    def capture_from_camera(self):
        if not self._current:
            QMessageBox.information(self, "Face ID", "Сначала найдите и выберите клиента")
            return
        dlg = CameraDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.photo_path:
            return
        self.lbl_photo.setPixmap(QPixmap(dlg.photo_path).scaled(
            180, 180, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self._register_path(dlg.photo_path)

    def register_photo(self):
        if not self._current:
            QMessageBox.information(self, "Face ID", "Сначала найдите и выберите клиента")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Фото клиента", "", "Изображения (*.jpg *.jpeg *.png *.bmp)")
        if not path:
            return
        self.lbl_photo.setPixmap(QPixmap(path).scaled(
            180, 180, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self._register_path(path)

    def _register_path(self, path):
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            QMessageBox.critical(self, "Фото", str(e))
            return
        self._last_b64 = b64   # ← добавить: запоминаем кадр для «Проверить меня»
        cid = str(self._current.get("id"))
        self._run(lambda: self.api.face_register(cid, b64), self._on_registered)

    def verify_me(self):
        """Проверка распознавания: текущий кадр → /face-id/verify."""
        b64 = getattr(self, "_last_b64", None)
        if not b64:
            QMessageBox.information(self, "Face ID",
                "Сначала снимите фото («📷 Снять с камеры» или «📂 Загрузить файл»)")
            return
        self._run(lambda: self.api.verify_face(b64), self._on_verify)

    def _on_registered(self, r):
        try:
            txt = json.dumps(r, ensure_ascii=False, indent=2, default=str)[:1500]
        except Exception:
            txt = str(r)
        ok = False
        if isinstance(r, dict):
            ok = bool(r.get("ok") or r.get("success") or r.get("id")
                      or r.get("template_id") or r.get("face_template_id"))
        self._show((" Шаблон зарегистрирован:\n" if ok else " Ответ сервера:\n") + txt)
        if ok:
            self.load_templates()

    # ---------- шаблоны / сервис ----------
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

    def engine_info(self):
        self._run(self.api.face_engine_info,
                  lambda r: self._show(json.dumps(r, ensure_ascii=False, indent=2, default=str)[:1200]))

    def engine_settings(self):
        try:
            cur = self.api.session.get(self.api._url("/face-id/settings"), timeout=30).json()
        except Exception as e:
            QMessageBox.warning(self, "Настройки", str(e)[:150])
            return
        t, ok = QInputDialog.getDouble(
            self, "Порог уверенности",
            "Евклидово расстояние dlib (меньше = строже; 0.6 — стандарт):",
            float(cur.get("threshold", 0.6)), 0.1, 1.5, 2)
        if not ok:
            return
        q, ok = QInputDialog.getDouble(
            self, "Мин. качество фото",
            "Порог резкости (Лапласиан; стандарт 40):",
            float(cur.get("min_quality", 40.0)), 1.0, 10000.0, 0)
        if not ok:
            return
        m, ok = QInputDialog.getInt(
            self, "Лимит шаблонов",
            "Максимум шаблонов на одного клиента:",
            int(cur.get("max_templates", 5)), 1, 20)
        if not ok:
            return
        sp, ok = QInputDialog.getItem(
            self, "Хранение фото лиц",
            "Сохранять сами фотографии на сервере?\n"
            "(по умолчанию — нет: только математические шаблоны; 152-ФЗ)",
            ["Нет", "Да, хранить фото"],
            1 if cur.get("store_photos") else 0, False)
        if not ok:
            return
        store_photos = sp.startswith("Да")
        try:
            r = self.api.session.put(self.api._url("/face-id/settings"),
                                     json={"threshold": t, "min_quality": q,
                                           "max_templates": m,
                                           "store_photos": store_photos},
                                     timeout=30)
            r.raise_for_status()
            self._show("Настройки движка сохранены: "
                       + json.dumps(r.json(), ensure_ascii=False))
        except Exception as e:
            QMessageBox.warning(self, "Настройки", str(e)[:150])
    def delete_template(self):
        row = self.tbl.currentRow()
        if row < 0:
            self._show("Сначала выберите шаблон в таблице", ok=False)
            return
        tid = self.tbl.item(row, 0).text()
        def _done(_r):
            self._show("Шаблон удалён")
            self.load_templates()
        self._run(lambda: self.api.delete_face_template(tid), _done)



    def sim_verify(self):
        self._run(lambda: self.api.verify_face(TEST_PHOTO), self._on_verify)

    def _on_verify(self, res):
        ok = isinstance(res, dict) and any(
            res.get(k) is True for k in ("verified", "access_granted", "match", "success", "allowed", "matched"))
        txt = json.dumps(res, ensure_ascii=False, indent=2, default=str)[:1200]
        self._show((" Доступ РАЗРЕШЁН\n" if ok else " Отказ / нет совпадения\n") + txt)


FaceIDTab = FaceIdTab  # алиас для совместимости с main_window