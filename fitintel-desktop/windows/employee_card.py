# -*- coding: utf-8 -*-
"""W12: Карточка сотрудника v2 — шапка + левое меню секций (компактная)."""
import datetime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem, QStackedWidget, QSplitter,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QAbstractItemView, QFrame, QApplication, QInputDialog)

from windows.form_dialog import FormDialog

_OPEN_CARDS = []


class EmployeeCard(QDialog):
    def __init__(self, api, user_id, user_data=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.user_id = str(user_id)
        self.user_data = user_data or {}
        self.setWindowTitle("Карточка сотрудника")
        self.resize(1080, 760)
        _OPEN_CARDS.append(self)
        self._u = {}
        self._depts = []

        root = QVBoxLayout(self)
        hb = QHBoxLayout()
        self.hdr = {}
        for key, title in (("fio", "Сотрудник"), ("role", "Роль"), ("dept", "Отдел"),
                           ("status", "Статус"), ("perms", "Прав"), ("created", "Принят")):
            box = QFrame()
            box.setStyleSheet("QFrame{background:#ffffff;border:1px solid #dfe3e8;border-radius:8px;}"
                              "QLabel{background:transparent;border:none;}")
            v = QVBoxLayout(box)
            t = QLabel(title); t.setStyleSheet("color:#637381;font-size:10px;")
            val = QLabel("—"); val.setStyleSheet("color:#212b36;font-size:13px;font-weight:700;")
            v.addWidget(t); v.addWidget(val)
            hb.addWidget(box, 1)
            self.hdr[key] = val
        root.addLayout(hb)

        ar = QHBoxLayout()
        for text, slot, color in (
                (" Сбросить пароль", self._reset_pwd, "#3b82f6"),
                (" Редактировать анкету", self._edit_profile, "#10b981"),
                (" Матрица ролей", self._open_roles, "#8b5cf6"),
                (" К зарплате", self._open_payroll, "#f59e0b")):
            b = QPushButton(text)
            b.setStyleSheet("QPushButton{background:%s;color:white;border:none;border-radius:6px;padding:8px 14px;font-weight:600;}" % color)
            b.clicked.connect(slot)
            ar.addWidget(b)
        ar.addStretch(1)
        root.addLayout(ar)

        sp = QSplitter(Qt.Orientation.Horizontal)
        self.menu = QListWidget()
        self.menu.setFixedWidth(200)
        self.menu.setStyleSheet(
            "QListWidget{background:#f8fafc;border:1px solid #e2e8f0;outline:none;}"
            "QListWidget::item{padding:7px 10px;color:#334155;}"
            "QListWidget::item:selected{background:#0ea5e9;color:white;}")
        sp.addWidget(self.menu)
        self.stack = QStackedWidget()
        sp.addWidget(self.stack)
        sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        self._pages = {}
        _idx = 0
        for section, items in (
                ("ДАННЫЕ", ["Анкета", "Фото"]),
                ("РАБОТА", ["График", "Расписание"]),
                ("ПРОЧЕЕ", ["Зарплата", "Доступы и браслеты"])):
            sec = QListWidgetItem(section)
            sec.setFlags(Qt.ItemFlag.NoItemFlags)
            sec.setForeground(QColor("#94a3b8"))
            self.menu.addItem(sec)
            for it in items:
                mi = QListWidgetItem(it)
                mi.setData(Qt.ItemDataRole.UserRole, _idx)
                self.menu.addItem(mi)
                page = QScrollArea(); page.setWidgetResizable(True)
                page.setWidget(QWidget())
                self._pages[it] = page
                self.stack.addWidget(page)
                _idx += 1
        self.menu.currentRowChanged.connect(self._on_menu)
        self.menu.setCurrentRow(1)
        QTimer.singleShot(60, self.reload)

    def _get(self, path, params=None):
        r = self.api.session.get(self.api._url(path), params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path, data=None):
        r = self.api.session.post(self.api._url(path), json=data or {}, timeout=30)
        r.raise_for_status()
        return r.json()

    def reload(self):
        u = None
        try:
            users = self.api.get_users()
            if isinstance(users, dict):
                users = users.get("items") or []
            for x in users or []:
                if str(x.get("id")) == self.user_id:
                    u = x
                    break
        except Exception:
            pass
        self._u = u or dict(self.user_data)
        try:
            self._depts = self._get("/analytics/departments").get("items", [])
        except Exception:
            self._depts = []
        self._fill_header()
        it = self.menu.currentItem()
        if it is not None and (it.flags() & Qt.ItemFlag.ItemIsEnabled):
            self._load_page(it.text())

    def _fill_header(self):
        u = self._u
        fio = (u.get("full_name") or "").strip() or str(u.get("username") or "—")
        self.setWindowTitle("Сотрудник: " + fio)
        self.hdr["fio"].setText(fio)
        roles = u.get("roles") or []
        self.hdr["role"].setText(
            ", ".join(str(r.get("name", r)) if isinstance(r, dict) else str(r) for r in roles) or "—")
        self.hdr["dept"].setText(str(u.get("department") or "—"))
        active = u.get("is_active")
        self.hdr["status"].setText("Активен" if active else "Отключён")
        self.hdr["status"].setStyleSheet(
            "color:%s;font-size:13px;font-weight:700;" % ("#059669" if active else "#ef4444"))
        perms = u.get("permissions") or []
        self.hdr["perms"].setText(str(len(perms)) if isinstance(perms, list) else "—")
        self.hdr["created"].setText(str(self._u.get("created_at") or "")[:10] or "—")

    def _on_menu(self, row):
        it = self.menu.item(row)
        if it is None or not (it.flags() & Qt.ItemFlag.ItemIsEnabled):
            return
        idx = it.data(Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.stack.setCurrentIndex(int(idx))
        self._load_page(it.text())

    def _layout(self, name):
        sc = self._pages[name]
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(10, 10, 10, 10)
        sc.setWidget(w)
        return v

    def _tbl(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        return t

    def _load_page(self, name):
        try:
            {"Анкета": self._p_profile, "Фото": self._p_photo,
             "График": self._p_stub, "Расписание": self._p_stub,
             "Зарплата": self._p_payroll, "Доступы и браслеты": self._p_access}.get(name, lambda: None)()
        except Exception as e:
            v = self._layout(name)
            v.addWidget(QLabel("Ошибка: %s" % str(e)[:180]))
            v.addStretch(1)

    def _p_profile(self):
        v = self._layout("Анкета")
        u = self._u
        grid = QGridLayout()
        rows = [("Логин", u.get("username")), ("Email", u.get("email")),
                ("ФИО", u.get("full_name")), ("Отдел", u.get("department")),
                ("ID", self.user_id[:12])]
        for i, (k, val) in enumerate(rows):
            l = QLabel(k + ":"); l.setStyleSheet("color:#637381;")
            grid.addWidget(l, i, 0)
            grid.addWidget(QLabel(str(val or "—")), i, 1)
        v.addLayout(grid)
        v.addStretch(1)

    def _p_photo(self):
        v = self._layout("Фото")
        self.ava = QLabel("—")
        self.ava.setFixedSize(140, 140)
        self.ava.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ava.setStyleSheet("background:#e2e8f0;border-radius:70px;color:#64748b;font-weight:700;")
        v.addWidget(self.ava, 0, Qt.AlignmentFlag.AlignHCenter)
        bar = QHBoxLayout()
        b_up = QPushButton(" Загрузить фото")
        b_up.clicked.connect(self._upload_photo)
        bar.addWidget(b_up)
        bar.addStretch(1)
        v.addLayout(bar)
        try:
            d = self._get("/analytics/w12/media/list", {"owner_type": "staff", "owner_id": self.user_id})
            items = d.get("items", [])
        except Exception:
            items = []
        t = self._tbl(["Файл", "Загружен"])
        t.setRowCount(len(items))
        for i, r in enumerate(items):
            t.setItem(i, 0, QTableWidgetItem(str(r.get("orig_name") or "")))
            t.setItem(i, 1, QTableWidgetItem(str(r.get("created_at") or "")[:19]))
        t.setMaximumHeight(200)
        v.addWidget(t)
        v.addWidget(QLabel("Фото — в защищённом медиа-хранилище (шифрование, UUID, доступ по правам)."))
        v.addStretch(1)
        for r in items:
            if str(r.get("photo_type") or "") != "document":
                url = str(r.get("url") or "")
                if url:
                    try:
                        full = url if url.startswith("http") else ("http://192.168.101.182" + url)
                        px = QPixmap()
                        px.loadFromData(self.api.session.get(full, timeout=15).content)
                        if not px.isNull():
                            self.ava.setPixmap(px.scaled(
                                140, 140, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation))
                    except Exception:
                        pass
                break

    def _upload_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Фото сотрудника", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        try:
            r = self.api.session.post(
                self.api._url("/analytics/w12/media/upload"),
                data={"owner_type": "staff", "owner_id": self.user_id, "photo_type": "avatar"},
                files={"file": open(path, "rb")}, timeout=90)
            r.raise_for_status()
            QMessageBox.information(self, "Фото", "Фото сохранено в защищённое хранилище")
            self._load_page("Фото")
        except Exception as e:
            QMessageBox.warning(self, "Фото", str(e)[:200])

    def _p_stub(self):
        name = "График" if self.menu.currentItem().text() == "График" else "Расписание"
        v = self._layout(name)
        v.addWidget(QLabel("Раздел в разработке: данные появятся после подключения серверного эндпоинта /schedules/."))
        v.addStretch(1)

    def _p_payroll(self):
        v = self._layout("Зарплата")
        v.addWidget(QLabel("Расчёт зарплаты — в «Бухгалтерия → Зарплата»:"))
        v.addWidget(QLabel("• штатное расписание → параметры сотрудника (оклад/ставка/комиссия);"))
        v.addWidget(QLabel("• начисления за месяц (аванс/удержания/штрафы/премия);"))
        v.addWidget(QLabel("• «Рассчитать» и «Выплачено» — с проводками 44/70 и 70/50."))
        b = QPushButton(" Открыть «Бухгалтерия → Зарплата»")
        b.clicked.connect(self._open_payroll)
        v.addWidget(b)
        v.addStretch(1)

    def _p_access(self):
        v = self._layout("Доступы и браслеты")
        b1 = QPushButton(" Выдать/привязать карту (RFID)")
        b1.clicked.connect(self._assign_card)
        v.addWidget(b1)
        v.addWidget(QLabel("Программирование замков, аренда шкафчиков, онлайн-замки — на экране «Браслеты/Карты»."))
        b2 = QPushButton(" Открыть «Браслеты/Карты»")
        b2.clicked.connect(lambda: self._nav("Браслеты"))
        v.addWidget(b2)
        v.addStretch(1)

    def _reset_pwd(self):
        p1, ok = QInputDialog.getText(self, "Сброс пароля", "Новый пароль (мин. 6 символов):")
        if not ok or not p1:
            return
        p2, ok2 = QInputDialog.getText(self, "Сброс пароля", "Повторите пароль:")
        if not ok2 or p1 != p2:
            QMessageBox.warning(self, "Пароль", "Пароли не совпадают")
            return
        try:
            r = self.api.session.post(self.api._url("/users/%s/reset-password" % self.user_id),
                                      json={"password": p1}, timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "Пароль", "Пароль сброшен")
        except Exception:
            try:
                r = self.api.session.patch(self.api._url("/users/%s" % self.user_id),
                                           json={"password": p1}, timeout=30)
                r.raise_for_status()
                QMessageBox.information(self, "Пароль", "Пароль изменён")
            except Exception as e2:
                QMessageBox.warning(self, "Пароль", str(e2)[:180])

    def _edit_profile(self):
        u = self._u
        cur = u.get("department") or ""
        combo = [(d, d) for d in self._depts] or [("(не задан)", "")]
        dlg = FormDialog("Анкета сотрудника", [
            ("full_name", "ФИО", "text", u.get("full_name") or ""),
            ("email", "Email", "text", u.get("email") or ""),
            ("department", "Отдел", "combo", combo),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val not in (None, "")}
        try:
            base = {k: v[k] for k in ("full_name", "email") if k in v}
            if base:
                r = self.api.session.patch(self.api._url("/users/%s" % self.user_id), json=base, timeout=30)
                r.raise_for_status()
            if "department" in v:
                self._post("/analytics/users/%s/department" % self.user_id, {"department": v["department"]})
            QMessageBox.information(self, "Анкета", "Сохранено")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Анкета", str(e)[:200])

    def _assign_card(self):
        uid, ok = QInputDialog.getText(self, "Выдать карту", "UID карты (пусто = сгенерировать):")
        if not ok:
            return
        try:
            r = self.api.session.post(self.api._url("/credentials/rfid/client/%s" % self.user_id),
                                      json={"uid": uid.strip() or None}, timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "Карта", "Карта привязана")
        except Exception:
            self._nav("Браслеты")

    def _open_roles(self):
        self._nav("Роли")

    def _open_payroll(self):
        self._nav("Бухгалтерия")

    def _nav(self, title):
        for w in QApplication.topLevelWidgets():
            lw = w.findChild(QListWidget)
            if lw is None:
                continue
            for i in range(lw.count()):
                if title.lower() in lw.item(i).text().lower():
                    lw.setCurrentRow(i)
                    try:
                        w.raise_(); w.activateWindow()
                    except Exception:
                        pass
                    return