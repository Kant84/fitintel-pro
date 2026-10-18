# -*- coding: utf-8 -*-
"""Карточка клиента: анкета / пакеты / визиты / статистика / заметки.
TODO(FastAPI): POST+GET /clients/{id}/comments, GET /comments."""
import requests as _requests
import windows.theme as theme
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSplitter, QScrollArea, QTabWidget, QWidget, QFormLayout, QGridLayout,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QTextEdit,
    QDateEdit, QMenu, QInputDialog, QMessageBox, QAbstractItemView)
from windows.icons import icon as _icon, polish as _polish
from app_logging import log

_STATUS_LABELS = {"ACTIVE": "Активен", "FROZEN": "Заморожен", "DEBTOR": "Должник",
                  "ARCHIVED": "Архив", "INACTIVE": "Неактивен"}
_METHOD_MAP = {"QR": "QR", "CARD": "Карта", "FACE_ID": "Face ID",
               "MANUAL": "Ручной", "OTHER": "Другое"}
_SUB_COLORS = {"ACTIVE": "#059669", "FROZEN": "#3b82f6",
               "EXPIRED": "#ef4444", "CANCELLED": "#94a3b8"}


class ClientCard(QDialog):
    def __init__(self, api, client_id: str, user_data=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.client_id = str(client_id)          # ПОЛНЫЙ UUID
        self.user_data = user_data or {}
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Карточка клиента")
        self.resize(1200, 800)
        self._client = None
        self._subs = []
        self._visits = []
        self._tariffs_map = {}
        self._build_ui()
        self._load()
        _polish(self)
        from windows.help_dialog import install_f1
        install_f1(self, "client_card")

    # ================= Загрузка =================
    class _Loader(QThread):
        client_ready = pyqtSignal(dict)
        subs_ready = pyqtSignal(list)
        visits_ready = pyqtSignal(list)
        tariffs_ready = pyqtSignal(list)
        error = pyqtSignal(str)

        def __init__(self, api, client_id):
            super().__init__()
            self.api = api
            self.client_id = client_id

        def run(self):
            try:
                # api.get_client() НЕТ → фильтруем из get_clients()
                clients = self.api.get_clients()
                client = next((c for c in clients
                               if str(c.get("id")) == str(self.client_id)), None)
                if client:
                    self.client_ready.emit(client)
                subs = [s for s in self.api.get_subscriptions()
                        if str(s.get("client_id")) == str(self.client_id)]
                self.subs_ready.emit(subs)
                # params — ВТОРОЙ аргумент dict; client_id — ПОЛНЫЙ UUID
                resp = self.api._e55_get(f"/visits/client/{self.client_id}",
                                         {"limit": 200, "offset": 0})
                visits = resp.get("items", []) if isinstance(resp, dict) else []
                self.visits_ready.emit(visits)
                self.tariffs_ready.emit(self.api.get_tariffs())
            except Exception as e:
                self.error.emit(str(e))

    def _load(self):
        self._loader = self._Loader(self.api, self.client_id)
        self._loader.client_ready.connect(self._on_client)
        self._loader.subs_ready.connect(self._on_subs)
        self._loader.visits_ready.connect(self._on_visits)
        self._loader.tariffs_ready.connect(self._on_tariffs)
        self._loader.error.connect(
            lambda m: QMessageBox.warning(self, "Ошибка загрузки", str(m)[:300]))
        self._loader.start()

    def _on_client(self, c):
        self._client = c
        self._render_left()
        self._render_right()
        self._render_anketa()

    def _on_subs(self, subs):
        self._subs = subs or []
        self._render_subs()

    def _on_visits(self, visits):
        self._visits = visits or []
        self._render_visits()
        self._render_stats()

    def _on_tariffs(self, tariffs):
        self._tariffs_map = {str(t.get("id")): t for t in (tariffs or [])}
        self._render_subs()

    # ================= UI-скелет =================
    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._left_layout, left_scroll = self._side_panel()
        splitter.addWidget(left_scroll)

        self._tabs = QTabWidget()
        splitter.addWidget(self._tabs)

        self._right_layout, right_scroll = self._side_panel()
        splitter.addWidget(right_scroll)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        main.addWidget(splitter, 1)

        self._t_anketa = self._add_tab("Анкета")
        self._t_subs = self._add_tab("Пакеты/Услуги")
        self._t_visits = self._add_tab("История визитов")
        self._t_stats = self._add_tab("Статистика посещений")
        self._t_notes = self._add_tab("Задачи и Заметки")

    def _side_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(260)
        scroll.setMaximumWidth(320)
        w = QWidget()
        lay = QVBoxLayout(w)
        scroll.setWidget(w)
        return lay, scroll

    def _add_tab(self, title):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(w)
        self._tabs.addTab(scroll, title)
        w._layout = lay
        return w

    def _clear(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    @staticmethod
    def _btn(text, color="#f1f5f9", fg="#475569"):
        b = QPushButton(text)
        b.setStyleSheet(f"QPushButton {{ background: {color}; color: {fg}; "
                        f"border: 1px solid #cbd5e1; border-radius: 6px; "
                        f"padding: 8px 14px; font-weight: 600; }}")
        return b

    def _fio(self, c=None):
        c = c or self._client or {}
        return " ".join(x for x in (c.get("last_name"), c.get("first_name"),
                                    c.get("middle_name")) if x) or "—"

    # ================= Левая панель =================
    def _render_left(self):
        self._clear(self._left_layout)
        c = self._client or {}

        avatar = QLabel(self._fio()[:2].upper())
        avatar.setFixedSize(180, 180)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("background: #3b82f6; color: white; font-size: 48px; border-radius: 90px;")
        self._left_layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignHCenter)

        b_photo = self._btn("Сменить фото")
        b_photo.clicked.connect(self._change_photo)
        self._left_layout.addWidget(b_photo)

        lbl_fio = QLabel(self._fio())
        f = lbl_fio.font(); f.setBold(True); f.setPointSize(14)
        lbl_fio.setFont(f); lbl_fio.setWordWrap(True)
        self._left_layout.addWidget(lbl_fio)

        age = ""
        bd = c.get("birth_date")
        if bd:
            try:
                from datetime import datetime as _dt
                age = f" · {_dt.now().year - _dt.fromisoformat(str(bd)[:10]).year} лет"
            except Exception:
                pass
        self._left_layout.addWidget(QLabel(f"ID: {self.client_id[:8]}...{age}"))

        self._left_layout.addWidget(QLabel("Статус:"))
        self._cb_status = QComboBox()
        for code in ("ACTIVE", "FROZEN", "DEBTOR", "ARCHIVED"):
            self._cb_status.addItem(_STATUS_LABELS.get(code, code), code)
        cur = str(c.get("status") or "ACTIVE").upper()
        idx = self._cb_status.findData(cur)
        if idx < 0:
            idx = self._cb_status.findData("ACTIVE")
        if idx >= 0:
            self._cb_status.setCurrentIndex(idx)
        self._cb_status.currentIndexChanged.connect(self._change_status)
        self._left_layout.addWidget(self._cb_status)

        b_sell = self._btn("Продать услугу", "#10b981", "white")
        b_sell.clicked.connect(lambda: QMessageBox.information(self, "Продажа", "Откройте вкладку Абонементы"))
        self._left_layout.addWidget(b_sell)

        b_card = self._btn("Выдать карту")
        b_card.clicked.connect(lambda: QMessageBox.information(self, "Карта", "Откройте экран Браслеты/Карты"))
        self._left_layout.addWidget(b_card)

        b_freeze = self._btn("Заморозить")
        b_freeze.clicked.connect(self._do_freeze)
        self._left_layout.addWidget(b_freeze)

        face_cnt = self._face_templates_count()
        self._left_layout.addWidget(QLabel(
            f"Face ID: {'привязан (' + str(face_cnt) + ')' if face_cnt else 'нет'}"))
        b_face = self._btn("Зарегистрировать")
        b_face.clicked.connect(lambda: QMessageBox.information(self, "Face ID", "Откройте экран Face ID"))
        self._left_layout.addWidget(b_face)
        self._left_layout.addStretch(1)

    def _change_status(self, _i):
        if not self._client or not self._cb_status:
            return
        new_status = self._cb_status.currentData()
        try:
            self.api.update_client(self.client_id, {
                "status": new_status, "is_active": (new_status == "ACTIVE")})
            self._client["status"] = new_status
            log.info("Статус клиента %s → %s", self.client_id[:8], new_status)
        except (RuntimeError, _requests.HTTPError) as e:
            self._show_error(e)
            cur = str((self._client or {}).get("status") or "ACTIVE").upper()
            self._cb_status.blockSignals(True)
            idx = self._cb_status.findData(cur)
            if idx >= 0:
                self._cb_status.setCurrentIndex(idx)
            self._cb_status.blockSignals(False)

    def _do_freeze(self):
        active_sub = next((s for s in self._subs if s.get("status") == "ACTIVE"), None)
        if not active_sub:
            QMessageBox.information(self, "Заморозка", "Нет активного абонемента")
            return
        try:
            self.api.freeze_subscription(active_sub["id"])
            QMessageBox.information(self, "Готово", "Абонемент заморожен")
            self._load()
        except (RuntimeError, _requests.HTTPError) as e:
            self._show_error(e)

    def _face_templates_count(self):
        try:
            templates = self.api.face_templates()
            if not isinstance(templates, list):
                return 0
            return sum(1 for t in templates
                       if isinstance(t, dict) and str(t.get("client_id")) == str(self.client_id))
        except Exception:
            return 0

    # ================= Анкета =================
    def _render_anketa(self):
        lay = self._t_anketa._layout
        self._clear(lay)
        c = self._client or {}
        form = QFormLayout()
        form.addRow("ФИО:", QLabel(self._fio()))
        form.addRow("Дата рождения:", QLabel(str(c.get("birth_date") or "—")))
        form.addRow("Пол:", QLabel({"MALE": "Мужской", "МУЖСКОЙ": "Мужской",
                                    "FEMALE": "Женский", "ЖЕНСКИЙ": "Женский"}.get(str(c.get("gender")), "—")))
        form.addRow("Телефон:", QLabel(str(c.get("phone") or "—")))
        form.addRow("Email:", QLabel(str(c.get("email") or "—")))
        form.addRow("Категория:", QLabel(str(c.get("client_category") or "—")))
        lay.addLayout(form)
        b_edit = self._btn("Редактировать")
        b_edit.clicked.connect(lambda: QMessageBox.information(
            self, "Редактирование", "Откройте экран Клиенты → Изменить"))
        lay.addWidget(b_edit)
        lay.addStretch(1)
        self._export_panel(lay, self._anketa_export)

    def _anketa_export(self, fmt=None):
        c = self._client or {}
        headers = ["ФИО", "Дата рождения", "Пол", "Телефон", "Email", "Категория"]
        rows = [[self._fio(), str(c.get("birth_date") or ""),
                 {"MALE": "Мужской", "FEMALE": "Женский"}.get(str(c.get("gender")), ""),
                 str(c.get("phone") or ""), str(c.get("email") or ""),
                 str(c.get("client_category") or "")]]
        return headers, rows, "Клиент: " + self._fio()

    # ================= Пакеты =================
    def _render_subs(self):
        lay = self._t_subs._layout
        self._clear(lay)
        tbl = QTableWidget(0, 6)
        tbl.setHorizontalHeaderLabels(["Название", "Тип", "Остаток", "Срок", "Статус", "Заморожен до"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(theme.table_style())
        for s in self._subs:
            r = tbl.rowCount()
            tbl.insertRow(r)
            tid = str(s.get("tariff_id"))
            name = (self._tariffs_map.get(tid) or {}).get("name") or tid[:8]
            if s.get("is_unlimited"):
                typ, ost = "Безлимит", "∞"
            elif s.get("visit_limit"):
                typ = "Пакет"
                ost = f"{s.get('visits_used', 0)}/{s.get('visit_limit')}"
            else:
                typ, ost = "Членство", "—"
            period = f"{(s.get('start_date') or '')[:10]}–{(s.get('end_date') or '')[:10]}"
            status = str(s.get("status") or "—")
            frozen = str(s.get("frozen_until") or "")[:10] if s.get("frozen_until") else "—"
            for col, val in enumerate([name, typ, ost, period, status, frozen]):
                item = QTableWidgetItem(str(val))
                if col == 4:
                    item.setForeground(QColor(_SUB_COLORS.get(status.upper(), "#0f172a")))
                tbl.setItem(r, col, item)
        lay.addWidget(tbl)
        self._t_subs._table = tbl
        lay.addStretch(1)
        self._export_panel(lay, lambda fmt=None: self._table_export(self._t_subs, "Пакеты клиента"))

    # ================= Визиты =================
    def _render_visits(self):
        lay = self._t_visits._layout
        self._clear(lay)
        tbl = QTableWidget(0, 7)
        tbl.setHorizontalHeaderLabels(["Дата", "Вход", "Выход", "Длит.", "Зона", "Способ", "Сотрудник"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(theme.table_style())
        for v in self._visits:
            r = tbl.rowCount()
            tbl.insertRow(r)
            entry = str(v.get("entry_time") or "")
            exit_ = str(v.get("exit_time") or "")
            dur = v.get("duration_minutes")
            vals = [
                entry[:10],
                entry[11:16] if len(entry) >= 16 else "—",
                exit_[11:16] if len(exit_) >= 16 else "—",
                f"{dur} мин" if dur else "—",
                str(v.get("zone") or "—"),
                _METHOD_MAP.get(str(v.get("access_method") or "OTHER"), "—"),
                str(v.get("processed_by_user_id") or "—")[:8],
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, str(v.get("id")))
                tbl.setItem(r, col, item)
        tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tbl.customContextMenuRequested.connect(lambda pos: self._visit_menu(tbl, pos))
        lay.addWidget(tbl)
        self._t_visits._table = tbl
        lay.addStretch(1)
        self._export_panel(lay, lambda fmt=None: self._table_export(self._t_visits, "Визиты клиента"))

    def _visit_menu(self, tbl, pos):
        item = tbl.itemAt(pos)
        if not item:
            return
        vid = item.data(Qt.ItemDataRole.UserRole)
        if not vid:
            return
        menu = QMenu(self)
        act_cancel = menu.addAction("Отменить визит")
        if menu.exec(tbl.viewport().mapToGlobal(pos)) != act_cancel:
            return
        reason, ok = QInputDialog.getText(self, "Отмена визита", "Причина:")
        if not ok or not reason.strip():
            return
        try:
            # DELETE с телом — только session.request
            self.api.session.request("DELETE", self.api._url(f"/visits/{vid}"),
                                     json={"reason": reason.strip()}, timeout=30)
            self._load()
        except (RuntimeError, _requests.HTTPError) as e:
            self._show_error(e)

    # ================= Статистика =================
    def _render_stats(self):
        lay = self._t_stats._layout
        self._clear(lay)
        visits = self._visits
        from datetime import datetime as _dt, timedelta as _td
        cutoff = (_dt.now() - _td(days=30)).isoformat()[:10]
        month_count = sum(1 for v in visits if (v.get("entry_time") or "")[:10] >= cutoff)
        durs = [v.get("duration_minutes") for v in visits if v.get("duration_minutes")]
        avg = int(sum(durs) / len(durs)) if durs else 0
        last = max((v.get("entry_time") or "") for v in visits) if visits else "—"
        grid = QGridLayout()
        for i, (title, val) in enumerate([
                ("Всего визитов", len(visits)),
                ("За месяц", month_count),
                ("Средняя длительность", f"{avg} мин"),
                ("Последний визит", str(last)[:16])]):
            card = QFrame()
            card.setStyleSheet(theme.card_style())
            cv = QVBoxLayout(card)
            tl = QLabel(title); tl.setStyleSheet("color: #64748b; font-size: 11px;")
            vl = QLabel(str(val)); f = vl.font(); f.setBold(True); f.setPointSize(14)
            vl.setFont(f)
            cv.addWidget(tl); cv.addWidget(vl)
            grid.addWidget(card, 0, i)
        lay.addLayout(grid)
        lay.addWidget(QLabel("Тренд по неделям:"))
        weeks = {}
        for v in visits:
            ts = (v.get("entry_time") or "")[:10]
            if not ts:
                continue
            try:
                d = _dt.fromisoformat(ts)
                y, wk, _ = d.isocalendar()
                key = f"{y}-W{wk:02d}"
                weeks[key] = weeks.get(key, 0) + 1
            except Exception:
                continue
        tbl = QTableWidget(len(weeks), 2)
        tbl.setHorizontalHeaderLabels(["Неделя", "Кол-во"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setStyleSheet(theme.table_style())
        for r, (wk, cnt) in enumerate(sorted(weeks.items())):
            tbl.setItem(r, 0, QTableWidgetItem(wk))
            tbl.setItem(r, 1, QTableWidgetItem(str(cnt)))
        lay.addWidget(tbl)
        self._t_stats._table = tbl
        lay.addStretch(1)
        self._export_panel(lay, lambda fmt=None: self._table_export(self._t_stats, "Статистика клиента"))

    # ================= Заметки =================
    def _render_notes(self):
        lay = self._t_notes._layout
        self._clear(lay)
        self._notes_list = QListWidget()
        self._notes_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._notes_list.customContextMenuRequested.connect(self._notes_menu)
        lay.addWidget(self._notes_list)
        form = QHBoxLayout()
        self._note_text = QTextEdit()
        self._note_text.setPlaceholderText("Текст заметки…")
        self._note_text.setMaximumHeight(80)
        form.addWidget(self._note_text, 1)
        col = QVBoxLayout()
        self._note_type = QComboBox()
        self._note_type.addItem("Заметка", "NOTE")
        self._note_type.addItem("Задача", "TASK")
        self._note_type.addItem("Звонок", "CALL")
        col.addWidget(self._note_type)
        self._note_due = QDateEdit(QDate.currentDate())
        self._note_due.setCalendarPopup(True)
        col.addWidget(self._note_due)
        form.addLayout(col)
        b_add = self._btn("Добавить", "#10b981", "white")
        b_add.clicked.connect(self._add_note)
        form.addWidget(b_add)
        lay.addLayout(form)
        self._load_notes()
        self._export_panel(lay, lambda fmt=None: self._notes_export())

    def _load_notes(self):
        try:
            resp = self.api._e55_get(f"/clients/{self.client_id}/comments")
            items = (resp.get("items", []) if isinstance(resp, dict)
                     else (resp if isinstance(resp, list) else []))
            self._notes_list.clear()
            for n in items:
                if not isinstance(n, dict):
                    continue
                it = QListWidgetItem(
                    f"{str(n.get('created_at') or '')[:16]} · "
                    f"{n.get('author_name') or '—'} · [{n.get('type') or 'NOTE'}] "
                    f"{(n.get('text') or '')[:80]}")
                it.setData(Qt.ItemDataRole.UserRole, str(n.get("id") or ""))
                self._notes_list.addItem(it)
            if not items:
                self._notes_list.addItem("Заметок нет")
        except (RuntimeError, _requests.HTTPError) as e:
            s = str(e)
            if "404" in s or "not found" in s.lower():
                self._notes_list.clear()
                self._notes_list.addItem("⏳ Заметки недоступны — эндпоинт /comments в разработке")
                self._note_text.setEnabled(False)
            else:
                self._show_error(e)

    def _add_note(self):
        text = self._note_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Заметка", "Введите текст")
            return
        try:
            self.api._e55_post(f"/clients/{self.client_id}/comments", {
                "text": text,
                "type": self._note_type.currentData(),
                "due_date": self._note_due.date().toString("yyyy-MM-dd"),
            })
            self._note_text.clear()
            self._load_notes()
        except (RuntimeError, _requests.HTTPError) as e:
            self._show_error(e)

    def _notes_export(self, fmt=None):
        headers = ["Заметка"]
        rows = [[self._notes_list.item(r).text()] for r in range(self._notes_list.count())]
        return headers, rows, "Заметки клиента"

    def _notes_menu(self, pos):
        item = self._notes_list.itemAt(pos)
        if not item:
            return
        cid = item.data(Qt.ItemDataRole.UserRole)
        if not cid:
            return
        menu = QMenu(self)
        a_done = menu.addAction("Отметить выполненным")
        a_del = menu.addAction("Удалить")
        act = menu.exec(self._notes_list.viewport().mapToGlobal(pos))
        try:
            if act == a_done:
                self.api._e55_patch(f"/comments/{cid}", {"status": "DONE"})
                self._load_notes()
            elif act == a_del:
                if QMessageBox.question(self, "Заметка", "Удалить запись?") == QMessageBox.StandardButton.Yes:
                    self.api._e55_del(f"/comments/{cid}")
                    self._load_notes()
        except (RuntimeError, _requests.HTTPError) as e:
            self._show_error(e)
    def _change_photo(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Фото клиента", "", "Images (*.jpg *.jpeg *.png)")
        if not path:
            return
        try:
            with open(path, "rb") as fh:
                self.api.session.post(
                    self.api._url(f"/clients/{self.client_id}/photo"),
                    files={"file": ("photo.jpg", fh, "image/jpeg")}, timeout=30)
            self._load()
        except (RuntimeError, _requests.HTTPError) as e:
            self._show_error(e)
    # ================= Правая панель =================
    def _render_right(self):
        self._clear(self._right_layout)
        c = self._client or {}
        finance = QFrame()
        finance.setStyleSheet(theme.card_style())
        fl = QVBoxLayout(finance)
        fl.addWidget(QLabel("Финансы"))
        wb = c.get("wallet_balance")
        if wb is not None:
            try:
                wb_float = float(wb)
                lbl = QLabel(f"Баланс ЛС: {wb_float:.2f} ₽")
                lbl.setStyleSheet(theme.banner_style(ok=(wb_float >= 0)))
                fl.addWidget(lbl)
            except (TypeError, ValueError):
                fl.addWidget(QLabel(f"Баланс ЛС: {wb}"))
        else:
            grey = QLabel("Нет доступа к финансам")
            grey.setStyleSheet("color: #94a3b8;")
            fl.addWidget(grey)
        bonuses = c.get("bonuses")
        fl.addWidget(QLabel(f"Бонусы: {bonuses if bonuses is not None else '—'}"))
        fl.addWidget(QLabel("Депозит: —"))
        self._right_layout.addWidget(finance)
        bookings = QFrame()
        bookings.setStyleSheet(theme.card_style())
        bl = QVBoxLayout(bookings)
        bl.addWidget(QLabel("Ближайшие брони"))
        bl.addWidget(QLabel("Нет данных"))
        self._right_layout.addWidget(bookings)
        self._right_layout.addStretch(1)

    # ================= Экспорт / ошибки =================
    def _table_export(self, tab_widget, title):
        tbl = getattr(tab_widget, "_table", None)
        headers = [tbl.horizontalHeaderItem(i).text() for i in range(tbl.columnCount())] if tbl else []
        rows = [[tbl.item(r, c).text() if tbl.item(r, c) else ""
                 for c in range(tbl.columnCount())] for r in range(tbl.rowCount())] if tbl else []
        return headers, rows, title

    def _export_panel(self, lay, data_fn):
        hb = QHBoxLayout()
        hb.addStretch()
        def _do(fmt):
            from windows.export_helper import (export_table_xlsx, export_table_pdf,
                                               export_counterparties_1c)
            try:
                if fmt == "1c":
                    export_counterparties_1c(self, [self._client] if self._client else [])
                    return
                headers, rows, title = data_fn(fmt)
                if fmt == "xlsx":
                    export_table_xlsx(self, headers, rows, "export", title)
                else:
                    export_table_pdf(self, headers, rows, "export", title)
            except (RuntimeError, _requests.HTTPError) as e:
                self._show_error(e)
        for fmt, label in [("xlsx", "XLSX"), ("pdf", "PDF"), ("1c", "1С")]:
            b = self._btn(label)
            b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; "
                            "border: 1px solid #cbd5e1; border-radius: 6px; "
                            "padding: 6px 12px; font-weight: 600; }")
            b.clicked.connect(lambda _, f=fmt: _do(f))
            hb.addWidget(b)
        lay.addLayout(hb)

    def _show_error(self, e):
        s = str(e)
        if "401" in s or "Unauthorized" in s:
            QMessageBox.warning(self, "Сессия", "Сессия истекла, войдите заново")
        elif "403" in s or "Нет прав" in s:
            QMessageBox.warning(self, "Нет прав", s[:300])
        elif "404" in s or "not found" in s.lower():
            QMessageBox.information(self, "Недоступно", "Раздел в разработке")
        else:
            QMessageBox.warning(self, "Ошибка", s[:300])