# -*- coding: utf-8 -*-
"""W11: Карточка клиента v2 — шапка + левое меню секций (классика F02000)."""
import datetime
import requests as _requests
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QSpinBox, QDateEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QSplitter, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QToolButton, QAbstractItemView, QFrame,
    QSizePolicy)

STATUS_LABELS = {"ACTIVE": "Активен", "FROZEN": "Заморожен", "DEBTOR": "Должник",
                 "ARCHIVED": "Архив", "INACTIVE": "Неактивен"}
STATUS_COLORS = {"ACTIVE": "#059669", "FROZEN": "#3b82f6", "DEBTOR": "#d97706",
                 "ARCHIVED": "#64748b", "INACTIVE": "#ef4444"}
KIND_LABELS = {"phone": "Телефон", "max": "MAX", "telegram": "Telegram", "email": "Email"}


def _fmt(iso):
    return str(iso or "")[:10]


class ClientCard(QDialog):
    def __init__(self, api, client_id, user_data=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.client_id = str(client_id)
        self.user_data = user_data or {}
        self.setWindowTitle("Карточка клиента")
        self.resize(1240, 820)
        self._client = {}
        self._profile = {}
        self._subs = []
        self._files = {"photos": [], "documents": []}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # ── Шапка ──
        hb = QHBoxLayout()
        self.hdr = {}
        for key, title in (("fio", "Клиент"), ("club", "Клуб"), ("tariff", "Тариф"),
                           ("card", "Карта"), ("dogovor", "Договор"), ("wallet", "Лиц. счёт"),
                           ("state", "Состояние")):
            box = QFrame()
            box.setStyleSheet("QFrame{background:#ffffff;border:1px solid #dfe3e8;border-radius:8px;}"
                              "QLabel{background:transparent;border:none;}")
            v = QVBoxLayout(box)
            v.setContentsMargins(8, 4, 8, 4)
            t = QLabel(title)
            t.setStyleSheet("color:#637381;font-size:10px;")
            val = QLabel("—")
            val.setStyleSheet("color:#212b36;font-size:13px;font-weight:700;")
            val.setWordWrap(True)
            v.addWidget(t)
            v.addWidget(val)
            hb.addWidget(box, 1)
            self.hdr[key] = val
        self.eye = QToolButton()
        self.eye.setText("👁")
        self.eye.setCheckable(True)
        self.eye.setToolTip("Конфиденциально: скрывать данные от ролей без права")
        self.eye.toggled.connect(self._toggle_confidential)
        hb.addWidget(self.eye)
        root.addLayout(hb)

        # ── Действия ──
        ar = QHBoxLayout()
        for text, slot, color in (
                (" Продать услугу", self._sell_service, "#10b981"),
                (" Выдать карту", self._assign_card, "#3b82f6"),
                (" Заморозить", self._freeze, "#f59e0b"),
                (" К сообщениям MAX", self._open_max, "#8b5cf6")):
            b = QPushButton(text)
            b.setStyleSheet("QPushButton{background:%s;color:white;border:none;border-radius:6px;padding:8px 14px;font-weight:600;}" % color)
            b.clicked.connect(slot)
            ar.addWidget(b)
        ar.addStretch(1)
        root.addLayout(ar)

        # ── Меню + страницы ──
        sp = QSplitter(Qt.Orientation.Horizontal)
        self.menu = QListWidget()
        self.menu.setFixedWidth(210)
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
                ("ДАННЫЕ", ["Анкета", "Телефоны/Контакты", "Документы", "Фото",
                            "Пакеты/Услуги", "Замечания"]),
                ("СЧЁТ", ["Чеки", "Баланс", "Бонусы", "Скидки"]),
                ("ПРОЧЕЕ", ["Сообщения", "История", "Блоки", "Автомобили", "Гость"])):
            sec = QListWidgetItem(section)
            sec.setFlags(Qt.ItemFlag.NoItemFlags)
            sec.setForeground(QColor("#94a3b8"))
            self.menu.addItem(sec)
            for it in items:
                mi = QListWidgetItem(it)
                mi.setData(Qt.ItemDataRole.UserRole, _idx)
                self.menu.addItem(mi)
                page = self._build_page(it)
                self._pages[it] = page
                self.stack.addWidget(page)
                _idx += 1
        self.menu.currentRowChanged.connect(self._on_menu)
        self.menu.setCurrentRow(1)

        hint = QLabel("Подсказка: двойной клик по строкам таблиц открывает детали; все списки обновляются кнопками «Обновить».")
        hint.setStyleSheet("color:#94a3b8;font-size:11px;")
        root.addWidget(hint)

        QTimer.singleShot(60, self.reload)

    # ================= data =================
    def _get(self, path, params=None):
        r = self.api.session.get(self.api._url(path), params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path, data=None):
        r = self.api.session.post(self.api._url(path), json=data or {}, timeout=30)
        r.raise_for_status()
        return r.json()

    def reload(self):
        try:
            d = self._get("/clients/%s" % self.client_id)
            self._client = d if isinstance(d, dict) else {}
        except Exception:
            self._client = {}
        try:
            d = self._get("/analytics/clients/%s/profile" % self.client_id)
            self._profile = d if isinstance(d, dict) else {}
        except Exception:
            self._profile = {}
        try:
            subs = self.api.get_subscriptions()
            if isinstance(subs, dict):
                subs = subs.get("items") or []
            self._subs = [s for s in (subs or [])
                          if str(s.get("client_id")) == self.client_id]
        except Exception:
            self._subs = []
        try:
            self._files = self._get("/analytics/clients/%s/files" % self.client_id)
        except Exception:
            self._files = {"photos": [], "documents": []}
        self._fill_header()
        name = self.menu.currentItem().text() if self.menu.currentItem() else "Анкета"
        self._load_page(name)

    def _fill_header(self):
        c, p = self._client, self._profile
        fio = " ".join(x for x in (c.get("last_name"), c.get("first_name"), c.get("middle_name")) if x) or "—"
        self.setWindowTitle("Карточка: " + fio)
        self.hdr["fio"].setText(fio)
        self.hdr["club"].setText(str(c.get("club_name") or "Основной клуб"))
        act = [s for s in self._subs if str(s.get("status", "")).upper() == "ACTIVE"]
        tname = "—"
        period = ""
        if act:
            tname = str(act[0].get("tariff_name") or act[0].get("tariff") or "Абонемент")
            period = "%s – %s" % (_fmt(act[0].get("start_date")), _fmt(act[0].get("end_date")))
        elif self._subs:
            tname = str(self._subs[-1].get("tariff_name") or "—")
        ck = (p.get("contract_kind") or "").strip()
        if ck:
            tname = "%s (%s)" % (tname, ck)
        self.hdr["tariff"].setText(tname)
        self.hdr["card"].setText(str(c.get("card_uid") or c.get("rfid_uid") or "—"))
        self.hdr["dogovor"].setText("№ анкеты " + self.client_id[:8])
        wb = c.get("wallet_balance")
        self.hdr["wallet"].setText(("%s ₽" % wb) if wb is not None else "—")
        st = str(c.get("status") or "—").upper()
        self.hdr["state"].setText(STATUS_LABELS.get(st, st) + (("  " + period) if period else ""))
        self.hdr["state"].setStyleSheet("color:%s;font-size:13px;font-weight:700;" % STATUS_COLORS.get(st, "#212b36"))
        self.eye.blockSignals(True)
        self.eye.setChecked(bool(p.get("confidential")))
        self.eye.blockSignals(False)

    # ================= pages =================
    def _wrap(self, inner):
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(inner)
        return sc

    def _build_page(self, name):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.addWidget(QLabel("Загрузка…"))
        return self._wrap(w)

    def _on_menu(self, row):
        it = self.menu.item(row)
        if it is None or not (it.flags() & Qt.ItemFlag.ItemIsEnabled):
            return
        _idx = it.data(Qt.ItemDataRole.UserRole)
        if _idx is not None:
            self.stack.setCurrentIndex(int(_idx))
        self._load_page(it.text())

    def _page_layout(self, name):
        sc = self._pages[name]
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(10, 10, 10, 10)
        sc.setWidget(w)
        return v

    def _load_page(self, name):
        try:
            {"Анкета": self._p_anketa, "Телефоны/Контакты": self._p_contacts,
             "Документы": self._p_docs, "Фото": self._p_photos,
             "Пакеты/Услуги": self._p_subs, "Замечания": self._p_comments,
             "Чеки": self._p_payments, "Баланс": self._p_wallet, "Бонусы": self._p_bonuses,
             "Скидки": self._p_discount, "Сообщения": self._p_messages,
             "История": self._p_history, "Блоки": self._p_blocks,
             "Автомобили": self._p_cars, "Гость": self._p_guest}.get(name, lambda: None)()
        except Exception as e:
            v = self._page_layout(name)
            v.addWidget(QLabel("Ошибка загрузки раздела: %s" % str(e)[:200]))
            v.addStretch(1)

    def _tbl(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setAlternatingRowColors(True)
        return t

    def _refresh_btn(self, fn):
        b = QPushButton(" Обновить")
        b.clicked.connect(fn)
        return b

    # ── Анкета ──
    def _p_anketa(self):
        v = self._page_layout("Анкета")
        c, p = self._client, self._profile
        top = QHBoxLayout()
        self.ava = QLabel("—")
        self.ava.setFixedSize(120, 120)
        self.ava.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ava.setStyleSheet("background:#e2e8f0;border-radius:60px;color:#64748b;font-size:28px;font-weight:700;")
        self._set_avatar(c.get("photo_url") or c.get("avatar_url"))
        top.addWidget(self.ava)
        bp = QPushButton("Сменить фото")
        bp.clicked.connect(self._change_photo)
        top.addWidget(bp, 0, Qt.AlignmentFlag.AlignBottom)
        ttl = QLabel(" ".join(x for x in (c.get("last_name"), c.get("first_name"), c.get("middle_name")) if x) or "—")
        ttl.setStyleSheet("font-size:20px;font-weight:700;color:#212b36;")
        sub = QLabel("ID: %s   ·   Телефон: %s   ·   Email: %s" % (
            self.client_id[:8], c.get("phone") or "—", c.get("email") or "—"))
        sub.setStyleSheet("color:#637381;")
        tv = QVBoxLayout()
        tv.addWidget(ttl)
        tv.addWidget(sub)
        tv.addStretch(1)
        top.addLayout(tv, 1)
        v.addLayout(top)

        grid = QGridLayout()
        rows = [
            ("Дата рождения", _fmt(c.get("birth_date")) or "—"), ("Пол", c.get("gender") or "—"),
            ("Категория", c.get("client_category") or "—"), ("Тег", c.get("client_tag") or "—"),
            ("Сегмент", c.get("segment") or "—"), ("Источник", c.get("source") or "—"),
            ("Паспорт", p.get("passport") or "—"), ("Гражданство", p.get("citizenship") or "—"),
            ("Семейное положение", p.get("marital_status") or "—"), ("Дети", p.get("children") or "—"),
            ("Домашний адрес", p.get("home_address") or "—"), ("Почтовый адрес", p.get("postal_address") or "—"),
            ("Компания", p.get("work_company") or "—"), ("Должность", p.get("work_position") or "—"),
            ("Вид договора", p.get("contract_kind") or "—"),
        ]
        for i, (k, val) in enumerate(rows):
            l = QLabel(k + ":")
            l.setStyleSheet("color:#637381;")
            grid.addWidget(l, i, 0)
            grid.addWidget(QLabel(str(val)), i, 1)
        v.addLayout(grid)
        br = QHBoxLayout()
        b1 = QPushButton(" Редактировать (основное)")
        b1.clicked.connect(self._edit_main)
        b2 = QPushButton(" Редактировать (паспорт, адреса, работа)")
        b2.clicked.connect(self._edit_extra)
        br.addWidget(b1)
        br.addWidget(b2)
        br.addStretch(1)
        v.addLayout(br)
        v.addStretch(1)

    def _set_avatar(self, url):
        if not url:
            return
        try:
            full = url if str(url).startswith("http") else (self.api.base_url.rstrip("/").replace("/api/v1", "") + str(url))
            r = self.api.session.get(full, timeout=15)
            px = QPixmap()
            px.loadFromData(r.content)
            if not px.isNull():
                self.ava.setPixmap(px.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except Exception:
            pass

    def _change_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Фото клиента", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        try:
            r = self.api.session.post(self.api._url("/clients/%s/photo" % self.client_id),
                                      files={"file": open(path, "rb")}, timeout=60)
            r.raise_for_status()
            QMessageBox.information(self, "Фото", "Фото обновлено")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Фото", "Не удалось загрузить фото: %s" % str(e)[:200])

    def _edit_main(self):
        from windows.form_dialog import FormDialog
        c = self._client
        dlg = FormDialog("Основные данные", [
            ("last_name", "Фамилия *", "text", c.get("last_name") or ""),
            ("first_name", "Имя *", "text", c.get("first_name") or ""),
            ("middle_name", "Отчество", "text", c.get("middle_name") or ""),
            ("phone", "Телефон *", "text", c.get("phone") or ""),
            ("email", "Email *", "text", c.get("email") or ""),
            ("gender", "Пол", "combo", [("Мужской", "MALE"), ("Женский", "FEMALE"), ("Не указан", "НЕ_УКАЗАН")]),
            ("birth_date", "Дата рождения (ГГГГ-ММ-ДД)", "text", _fmt(c.get("birth_date"))),
            ("client_tag", "Тег", "text", c.get("client_tag") or ""),
            ("segment", "Сегмент", "text", c.get("segment") or ""),
            ("source", "Источник", "text", c.get("source") or ""),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val not in (None, "")}
        try:
            self.api.update_client(self.client_id, v)
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Сохранение", str(e)[:200])

    def _edit_extra(self):
        from windows.form_dialog import FormDialog
        p = self._profile
        dlg = FormDialog("Дополнительные данные", [
            ("passport", "Паспорт (серия/номер)", "text", p.get("passport") or ""),
            ("citizenship", "Гражданство", "text", p.get("citizenship") or ""),
            ("marital_status", "Семейное положение", "text", p.get("marital_status") or ""),
            ("children", "Дети", "text", p.get("children") or ""),
            ("home_address", "Домашний адрес", "text", p.get("home_address") or ""),
            ("postal_address", "Почтовый адрес", "text", p.get("postal_address") or ""),
            ("work_company", "Компания", "text", p.get("work_company") or ""),
            ("work_position", "Должность", "text", p.get("work_position") or ""),
            ("contract_kind", "Вид договора (абонемент/разовое/услуга/занятие)", "text", p.get("contract_kind") or ""),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val not in (None, "")}
        try:
            self._post("/analytics/clients/%s/profile" % self.client_id, v)
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Сохранение", str(e)[:200])

    # ── Контакты ──
    def _p_contacts(self):
        v = self._page_layout("Телефоны/Контакты")
        self.tbl_contacts = self._tbl(["Тип", "Вид", "Значение", "Основной"])
        v.addWidget(self.tbl_contacts, 1)
        bar = QHBoxLayout()
        self.cb_ckind = QComboBox()
        for k, lab in KIND_LABELS.items():
            self.cb_ckind.addItem(lab, k)
        self.ed_ctype = QLineEdit(); self.ed_ctype.setPlaceholderText("Вид (Мобильный, Рабочий…)") 
        self.ed_cval = QLineEdit(); self.ed_cval.setPlaceholderText("Значение (+7…, @max, @telegram, email)")
        b_add = QPushButton(" Добавить"); b_add.clicked.connect(self._contact_add)
        b_del = QPushButton(" Удалить выбранный"); b_del.clicked.connect(self._contact_del)
        bar.addWidget(self.cb_ckind); bar.addWidget(self.ed_ctype, 1); bar.addWidget(self.ed_cval, 1)
        bar.addWidget(b_add); bar.addWidget(b_del)
        bar.addWidget(self._refresh_btn(self.reload))
        v.addLayout(bar)
        try:
            d = self._get("/analytics/clients/%s/contacts" % self.client_id)
            rows = d.get("items", [])
        except Exception:
            rows = []
        self.tbl_contacts.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.tbl_contacts.setItem(i, 0, QTableWidgetItem(KIND_LABELS.get(r.get("kind"), str(r.get("kind")))))
            self.tbl_contacts.setItem(i, 1, QTableWidgetItem(str(r.get("type_label") or "—")))
            self.tbl_contacts.setItem(i, 2, QTableWidgetItem(str(r.get("value") or "—")))
            self.tbl_contacts.setItem(i, 3, QTableWidgetItem("★" if r.get("is_primary") else ""))
            self.tbl_contacts.item(i, 0).setData(Qt.ItemDataRole.UserRole, r.get("id"))

    def _contact_add(self):
        val = self.ed_cval.text().strip()
        if not val:
            return
        try:
            self._post("/analytics/clients/%s/contacts" % self.client_id,
                       {"kind": self.cb_ckind.currentData(),
                        "type_label": self.ed_ctype.text().strip(),
                        "value": val, "is_primary": False})
            self.ed_cval.clear()
            self._load_page("Телефоны/Контакты")
        except Exception as e:
            QMessageBox.warning(self, "Контакт", str(e)[:200])

    def _contact_del(self):
        row = self.tbl_contacts.currentRow()
        if row < 0:
            return
        it = self.tbl_contacts.item(row, 0)
        cid2 = it.data(Qt.ItemDataRole.UserRole) if it else None
        if not cid2:
            return
        try:
            r = self.api.session.delete(self.api._url("/analytics/clients/%s/contacts/%s" % (self.client_id, cid2)), timeout=20)
            r.raise_for_status()
            self._load_page("Телефоны/Контакты")
        except Exception as e:
            QMessageBox.warning(self, "Контакт", str(e)[:200])

    # ── Документы ──
    def _p_docs(self):
        v = self._page_layout("Документы")
        self.tbl_docs = self._tbl(["Файл", "Действия"])
        v.addWidget(self.tbl_docs, 1)
        bar = QHBoxLayout()
        b_up = QPushButton(" Загрузить файл (договор, справка…)"); b_up.clicked.connect(lambda: self._upload("documents"))
        b_op = QPushButton("Открыть"); b_op.clicked.connect(lambda: self._file_open("documents"))
        b_del = QPushButton("Удалить"); b_del.clicked.connect(lambda: self._file_del("documents"))
        bar.addWidget(b_up); bar.addWidget(b_op); bar.addWidget(b_del)
        bar.addWidget(self._refresh_btn(self.reload))
        bar.addStretch(1)
        v.addLayout(bar)
        rows = self._files.get("documents", [])
        self.tbl_docs.setRowCount(len(rows))
        for i, r in enumerate(rows):
            it = QTableWidgetItem(r.get("name", ""))
            it.setData(Qt.ItemDataRole.UserRole, r.get("url"))
            self.tbl_docs.setItem(i, 0, it)
            self.tbl_docs.setItem(i, 1, QTableWidgetItem("«Открыть» выше"))

    # ── Фото ──
    def _p_photos(self):
        v = self._page_layout("Фото")
        self.tbl_photos = self._tbl(["Файл", "Действия"])
        v.addWidget(self.tbl_photos, 1)
        bar = QHBoxLayout()
        b_up = QPushButton(" Загрузить фото"); b_up.clicked.connect(lambda: self._upload("photos"))
        b_op = QPushButton("Открыть"); b_op.clicked.connect(lambda: self._file_open("photos"))
        b_del = QPushButton("Удалить"); b_del.clicked.connect(lambda: self._file_del("photos"))
        bar.addWidget(b_up); bar.addWidget(b_op); bar.addWidget(b_del)
        bar.addWidget(self._refresh_btn(self.reload))
        bar.addStretch(1)
        v.addLayout(bar)
        rows = self._files.get("photos", [])
        self.tbl_photos.setRowCount(len(rows))
        for i, r in enumerate(rows):
            it = QTableWidgetItem(r.get("name", ""))
            it.setData(Qt.ItemDataRole.UserRole, r.get("url"))
            self.tbl_photos.setItem(i, 0, it)
            self.tbl_photos.setItem(i, 1, QTableWidgetItem("«Открыть» выше"))

    def _upload(self, kind):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "",
            "Images (*.png *.jpg *.jpeg)" if kind == "photos" else "All (*.*)")
        if not path:
            return
        try:
            r = self.api.session.post(
                self.api._url("/analytics/clients/%s/files" % self.client_id),
                data={"kind": "Documents" if kind == "documents" else "Photos"},
                files={"file": open(path, "rb")}, timeout=120)
            r.raise_for_status()
            QMessageBox.information(self, "Загрузка", "Файл сохранён в папку клиента (Clients/%s/%s/)" % (self.client_id, "Documents" if kind == "documents" else "Photos"))
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Загрузка", str(e)[:250])

    def _file_open(self, kind):
        tbl = self.tbl_docs if kind == "documents" else self.tbl_photos
        row = tbl.currentRow()
        if row < 0:
            return
        it = tbl.item(row, 0)
        url = it.data(Qt.ItemDataRole.UserRole) if it else None
        if url:
            import os
            full = url if str(url).startswith("http") else ("http://192.168.101.182" + str(url))
            os.startfile(full)

    def _file_del(self, kind):
        tbl = self.tbl_docs if kind == "documents" else self.tbl_photos
        row = tbl.currentRow()
        if row < 0:
            return
        it = tbl.item(row, 0)
        url = it.data(Qt.ItemDataRole.UserRole) if it else None
        name = str(url).rsplit("/", 1)[-1] if url else ""
        if not name:
            return
        try:
            r = self.api.session.delete(self.api._url(
                "/analytics/clients/%s/files/%s/%s" % (self.client_id, "Documents" if kind == "documents" else "Photos", name)), timeout=20)
            r.raise_for_status()
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Удаление", str(e)[:200])

    # ── Пакеты/Услуги ──
    def _p_subs(self):
        v = self._page_layout("Пакеты/Услуги")
        t = self._tbl(["Название", "Тип", "Остаток", "Срок", "Статус", "Заморожен до"])
        v.addWidget(t, 1)
        for i, s in enumerate(self._subs):
            t.insertRow(i)
            t.setItem(i, 0, QTableWidgetItem(str(s.get("tariff_name") or s.get("tariff") or "—")))
            if s.get("is_unlimited"):
                typ, ost = "Безлимит", "∞"
            elif s.get("visit_limit"):
                typ, ost = "Пакет", "%s/%s" % (s.get("visits_used") or 0, s.get("visit_limit"))
            else:
                typ, ost = "Членство", "—"
            t.setItem(i, 1, QTableWidgetItem(typ))
            t.setItem(i, 2, QTableWidgetItem(str(ost)))
            t.setItem(i, 3, QTableWidgetItem("%s – %s" % (_fmt(s.get("start_date")), _fmt(s.get("end_date")))))
            st = str(s.get("status", "")).upper()
            it = QTableWidgetItem(st)
            it.setForeground(QColor(STATUS_COLORS.get(st, "#212b36")))
            t.setItem(i, 4, it)
            t.setItem(i, 5, QTableWidgetItem(_fmt(s.get("frozen_until")) or "—"))

    # ── Замечания ──
    def _p_comments(self):
        v = self._page_layout("Замечания")
        self.ed_note = QLineEdit(); self.ed_note.setPlaceholderText("Текст заметки/задачи…")
        self.cb_ntype = QComboBox()
        for lab, code in (("Заметка", "NOTE"), ("Задача", "TASK"), ("Звонок", "CALL")):
            self.cb_ntype.addItem(lab, code)
        b = QPushButton(" Добавить"); b.clicked.connect(self._note_add)
        bar = QHBoxLayout()
        bar.addWidget(self.ed_note, 1); bar.addWidget(self.cb_ntype); bar.addWidget(b)
        v.addLayout(bar)
        self.lst_notes = QListWidget()
        v.addWidget(self.lst_notes, 1)
        v.addWidget(self._refresh_btn(self.reload))
        try:
            d = self._get("/comments", {"client_id": self.client_id})
            rows = d.get("items", d if isinstance(d, list) else [])
        except Exception:
            rows = []
        for r in rows or []:
            self.lst_notes.addItem("%s · %s · [%s] %s" % (str(r.get("created_at") or "")[:16],
                r.get("author") or r.get("author_name") or "—", r.get("type") or "NOTE", r.get("text") or ""))

    def _note_add(self):
        txt = self.ed_note.text().strip()
        if not txt:
            return
        try:
            self._post("/comments", {"client_id": self.client_id, "text": txt,
                                     "type": self.cb_ntype.currentData()})
            self.ed_note.clear()
            self._load_page("Замечания")
        except Exception as e:
            QMessageBox.warning(self, "Замечание", str(e)[:200])

    # ── Чеки / Баланс / Бонусы ──
    def _p_payments(self):
        v = self._page_layout("Чеки")
        t = self._tbl(["Дата", "Сумма", "Способ", "Статус", "Комментарий"])
        v.addWidget(t, 1)
        v.addWidget(self._refresh_btn(self.reload))
        try:
            d = self._get("/payments/", {"client_id": self.client_id})
            rows = d.get("items", d if isinstance(d, list) else [])
        except Exception:
            rows = []
        for i, p in enumerate(rows or []):
            t.insertRow(i)
            t.setItem(i, 0, QTableWidgetItem(str(p.get("created_at") or "")[:16]))
            t.setItem(i, 1, QTableWidgetItem(str(p.get("amount") or 0)))
            t.setItem(i, 2, QTableWidgetItem(str(p.get("method") or p.get("payment_method") or "—")))
            t.setItem(i, 3, QTableWidgetItem(str(p.get("status") or "—")))
            t.setItem(i, 4, QTableWidgetItem(str(p.get("comment") or p.get("description") or "")[:80]))

    def _p_wallet(self):
        v = self._page_layout("Баланс")
        wb = self._client.get("wallet_balance")
        big = QLabel(("%s ₽" % wb) if wb is not None else "—")
        big.setStyleSheet("font-size:34px;font-weight:700;color:#059669;")
        v.addWidget(big)
        v.addWidget(QLabel("Лицевой счёт клиента (кошелёк приложения). Пополнение — через приложение/бота или администратором."))
        v.addStretch(1)

    def _p_bonuses(self):
        v = self._page_layout("Бонусы")
        bn = self._client.get("bonuses")
        big = QLabel(str(bn) if bn is not None else "—")
        big.setStyleSheet("font-size:34px;font-weight:700;color:#8b5cf6;")
        v.addWidget(big)
        v.addWidget(QLabel("Бонусные баллы. Правила начисления задаются в «Параметры клуба → Бонусы»."))
        v.addStretch(1)

    def _p_discount(self):
        v = self._page_layout("Скидки")
        cur = self._profile.get("discount_percent") or 0
        row = QHBoxLayout()
        row.addWidget(QLabel("Персональная скидка, %:"))
        self.sp_disc = QSpinBox(); self.sp_disc.setRange(0, 100); self.sp_disc.setValue(int(float(cur)))
        row.addWidget(self.sp_disc)
        b = QPushButton("Сохранить"); b.clicked.connect(self._discount_save)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(QLabel("Применяется менеджером при продаже (фиксируйте в комментарии платежа)."))
        v.addStretch(1)

    def _discount_save(self):
        try:
            self._post("/analytics/clients/%s/profile" % self.client_id,
                       {"discount_percent": self.sp_disc.value()})
            QMessageBox.information(self, "Скидка", "Сохранено")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Скидка", str(e)[:200])

    # ── Сообщения / История / Блоки / Авто / Гость ──
    def _p_messages(self):
        v = self._page_layout("Сообщения")
        v.addWidget(QLabel("Переписка с клиентом в MAX."))
        b = QPushButton(" Открыть MAX сообщения"); b.clicked.connect(self._open_max)
        v.addWidget(b)
        v.addWidget(QLabel("Контакты клиента (MAX/Telegram) — в разделе «Телефоны/Контакты»."))
        v.addStretch(1)

    def _p_history(self):
        v = self._page_layout("История")
        t = self._tbl(["Дата", "Вход", "Выход", "Зона", "Способ"])
        v.addWidget(t, 1)
        v.addWidget(self._refresh_btn(self.reload))
        try:
            d = self._get("/visits/", {"client_id": self.client_id})
            rows = d.get("items", d.get("visits", d if isinstance(d, list) else []))
        except Exception:
            rows = []
        for i, x in enumerate(rows or []):
            t.insertRow(i)
            t.setItem(i, 0, QTableWidgetItem(str(x.get("entry_time") or x.get("created_at") or "")[:16]))
            t.setItem(i, 1, QTableWidgetItem(str(x.get("entry_time") or "")[11:16]))
            t.setItem(i, 2, QTableWidgetItem(str(x.get("exit_time") or "")[11:16] or "—"))
            t.setItem(i, 3, QTableWidgetItem(str(x.get("zone") or "—")))
            t.setItem(i, 4, QTableWidgetItem(str(x.get("method") or x.get("access_method") or "—")))

    def _p_blocks(self):
        v = self._page_layout("Блоки")
        self.chk_block = QCheckBox("Вход заблокирован (чёрный список)")
        self.chk_block.setChecked(bool(self._profile.get("blocked")))
        v.addWidget(self.chk_block)
        self.ed_breason = QLineEdit(); self.ed_breason.setPlaceholderText("Причина блокировки")
        self.ed_breason.setText(str(self._profile.get("blocked_reason") or ""))
        v.addWidget(self.ed_breason)
        b = QPushButton("Сохранить"); b.clicked.connect(self._block_save)
        v.addWidget(b)
        v.addStretch(1)

    def _block_save(self):
        try:
            self._post("/analytics/clients/%s/profile" % self.client_id,
                       {"blocked": bool(self.chk_block.isChecked()),
                        "blocked_reason": self.ed_breason.text().strip()})
            QMessageBox.information(self, "Блоки", "Сохранено")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Блоки", str(e)[:200])

    def _p_cars(self):
        v = self._page_layout("Автомобили")
        self.tbl_cars = self._tbl(["Марка", "Номер", "Примечание"])
        v.addWidget(self.tbl_cars, 1)
        bar = QHBoxLayout()
        self.ed_car_m = QLineEdit(); self.ed_car_m.setPlaceholderText("Марка/модель")
        self.ed_car_n = QLineEdit(); self.ed_car_n.setPlaceholderText("Гос. номер")
        self.ed_car_t = QLineEdit(); self.ed_car_t.setPlaceholderText("Примечание")
        b_add = QPushButton(" Добавить"); b_add.clicked.connect(self._car_add)
        b_del = QPushButton(" Удалить выбранный"); b_del.clicked.connect(self._car_del)
        for w in (self.ed_car_m, self.ed_car_n, self.ed_car_t):
            bar.addWidget(w, 1)
        bar.addWidget(b_add); bar.addWidget(b_del)
        bar.addWidget(self._refresh_btn(self.reload))
        v.addLayout(bar)
        try:
            d = self._get("/analytics/clients/%s/cars" % self.client_id)
            rows = d.get("items", [])
        except Exception:
            rows = []
        self.tbl_cars.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.tbl_cars.setItem(i, 0, QTableWidgetItem(str(r.get("mark") or "—")))
            self.tbl_cars.setItem(i, 1, QTableWidgetItem(str(r.get("number") or "—")))
            self.tbl_cars.setItem(i, 2, QTableWidgetItem(str(r.get("note") or "—")))
            self.tbl_cars.item(i, 0).setData(Qt.ItemDataRole.UserRole, r.get("id"))

    def _car_add(self):
        if not self.ed_car_n.text().strip():
            return
        try:
            self._post("/analytics/clients/%s/cars" % self.client_id,
                       {"mark": self.ed_car_m.text().strip(),
                        "number": self.ed_car_n.text().strip(),
                        "note": self.ed_car_t.text().strip()})
            self.ed_car_m.clear(); self.ed_car_n.clear(); self.ed_car_t.clear()
            self._load_page("Автомобили")
        except Exception as e:
            QMessageBox.warning(self, "Авто", str(e)[:200])

    def _car_del(self):
        row = self.tbl_cars.currentRow()
        if row < 0:
            return
        it = self.tbl_cars.item(row, 0)
        cid2 = it.data(Qt.ItemDataRole.UserRole) if it else None
        if not cid2:
            return
        try:
            r = self.api.session.delete(self.api._url("/analytics/clients/%s/cars/%s" % (self.client_id, cid2)), timeout=20)
            r.raise_for_status()
            self._load_page("Автомобили")
        except Exception as e:
            QMessageBox.warning(self, "Авто", str(e)[:200])

    def _p_guest(self):
        v = self._page_layout("Гость")
        v.addWidget(QLabel("Гостевой пропуск / примечание о госте:"))
        self.ed_guest = QLineEdit()
        self.ed_guest.setText(str(self._profile.get("guest_note") or ""))
        self.ed_guest.setPlaceholderText("Напр.: гостевой визит до 25.10, сопровождает Сидорова А.")
        v.addWidget(self.ed_guest)
        b = QPushButton("Сохранить"); b.clicked.connect(self._guest_save)
        v.addWidget(b)
        v.addStretch(1)

    def _guest_save(self):
        try:
            self._post("/analytics/clients/%s/profile" % self.client_id,
                       {"guest_note": self.ed_guest.text().strip()})
            QMessageBox.information(self, "Гость", "Сохранено")
        except Exception as e:
            QMessageBox.warning(self, "Гость", str(e)[:200])

    # ================= actions =================
    def _toggle_confidential(self, on):
        try:
            self._post("/analytics/clients/%s/profile" % self.client_id, {"confidential": bool(on)})
        except Exception as e:
            QMessageBox.warning(self, "Конфиденциально", str(e)[:200])

    def _sell_service(self):
        from windows.form_dialog import FormDialog
        try:
            d = self._get("/tariffs")
            tariffs = d.get("items", d if isinstance(d, list) else [])
        except Exception:
            tariffs = []
        if not tariffs:
            QMessageBox.information(self, "Продажа", "Нет доступных тарифов")
            return
        combo = [(str(t.get("name") or t.get("id")), t.get("id")) for t in tariffs]
        dlg = FormDialog("Продать услугу", [
            ("tariff", "Тариф *", "combo", combo),
            ("start_date", "Дата начала (ГГГГ-ММ-ДД)", "text",
             datetime.date.today().isoformat()),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        val = dlg.values()
        payload = {"client_id": self.client_id, "tariff_id": val.get("tariff")}
        if val.get("start_date"):
            payload["start_date"] = val["start_date"]
        try:
            self._post("/subscriptions", payload)
            QMessageBox.information(self, "Продажа", "Абонемент создан")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Продажа", str(e)[:250])

    def _assign_card(self):
        from PyQt6.QtWidgets import QInputDialog
        uid, ok = QInputDialog.getText(self, "Выдать карту", "UID карты (пусто = сгенерировать):")
        if not ok:
            return
        try:
            r = self.api.session.post(self.api._url("/credentials/rfid/client/%s" % self.client_id),
                                      json={"uid": uid.strip() or None}, timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "Карта", "Карта привязана")
        except Exception:
            self._open_max_screen("Браслеты")

    def _freeze(self):
        act = [s for s in self._subs if str(s.get("status", "")).upper() == "ACTIVE"]
        if not act:
            QMessageBox.information(self, "Заморозка", "Нет активного абонемента")
            return
        sid = act[0].get("id")
        try:
            r = self.api.session.post(self.api._url("/subscriptions/%s/freeze" % sid), json={}, timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "Заморозка", "Абонемент заморожен")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Заморозка", str(e)[:250])

    def _open_max(self):
        self._open_max_screen("MAX")

    def _open_max_screen(self, title):
        from PyQt6.QtWidgets import QApplication, QListWidget
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