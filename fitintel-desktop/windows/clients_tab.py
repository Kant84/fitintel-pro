# -*- coding: utf-8 -*-
"""FitIntel Pro — Clients Tab: CRUD + фильтры + карточка клиента (двойной клик)."""
import requests as _requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox,
    QSpinBox, QDateEdit, QCheckBox, QToolButton, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QMessageBox,
    QAbstractItemView)
from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog
from app_logging import log


def _fmt_date(iso: str) -> str:
    s = str(iso or "")[:10]
    if len(s) == 10 and s[4] == "-":
        y, m, d = s.split("-")
        return f"{d}-{m}-{y}"
    return s


class ClientsWorker(QThread):
    """Один поток: клиенты + абонементы + пользователи (менеджеры)."""
    finished = pyqtSignal(list, list, list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            clients = self.api.get_clients()
            try:
                subs = self.api.get_subscriptions()
            except Exception:
                subs = []
            try:
                users = self.api.get_users()
            except Exception:
                users = []
            self.finished.emit(clients, subs, users)
        except Exception as e:
            self.error.emit(str(e))


CLIENT_FIELDS = [
    ("last_name", "Фамилия *"),
    ("first_name", "Имя *"),
    ("middle_name", "Отчество"),
    ("phone", "Телефон *", "text", "+7"),
    ("email", "Email *"),
    ("gender", "Пол", "combo", [("Мужской", "MALE"), ("Женский", "FEMALE"), ("Не указан", "НЕ_УКАЗАН")]),
    ("birth_date", "Дата рождения (ДД-ММ-ГГГГ)"),
]

CAT_LABELS = {"ADULT": "Взрослый", "CHILD": "Ребёнок", "VIP": "VIP", "STAFF": "Персонал",
              "НЕ_УКАЗАНА": "—", "ПЕНСИОНЕР": "Пенсионер", "ИНВАЛИД": "Инвалид",
              "КОРПОРАТИВНЫЙ": "Корпоративный"}

GENDER_MAP = {"Мужской": "MALE", "М": "MALE", "MALE": "MALE",
              "Женский": "FEMALE", "Ж": "FEMALE", "FEMALE": "FEMALE",
              "Не указан": "НЕ_УКАЗАН", "НЕ_УКАЗАН": "НЕ_УКАЗАН", "": "НЕ_УКАЗАН"}

STATUS_LABELS = {"ACTIVE": "Активен", "FROZEN": "Заморожен", "DEBTOR": "Должник",
                 "ARCHIVED": "Архив", "INACTIVE": "Неактивен"}


def _norm_gender(v: dict):
    if v.get("gender"):
        v["gender"] = GENDER_MAP.get(str(v["gender"]), "НЕ_УКАЗАН")
    return v


def _norm_birth_date(v: dict, parent) -> bool:
    if "birth_date" not in v:
        return True
    bd = str(v["birth_date"]).strip()
    if not bd:
        return True
    if len(bd) == 10 and bd[4] == "-" and bd[7] == "-":
        return True
    if len(bd) == 10 and bd[2] in ".-" and bd[5] in ".-":
        sep = bd[2]
        try:
            d, m, y = bd.split(sep)
            if len(y) != 4:
                raise ValueError
            v["birth_date"] = f"{y}-{m}-{d}"
            return True
        except Exception:
            pass
    QMessageBox.warning(parent, "Ошибка",
                        f"Неверный формат даты: {bd}\nИспользуйте ДД-ММ-ГГГГ (год четырёхзначный)")
    return False


class ClientsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._all_data = []
        self._subs = []
        self._users = []
        self._build_ui()
        self.refresh()

    # ---------- UI ----------
    def _btn(self, text, color="#f1f5f9", fg="#475569"):
        b = QPushButton(text)
        b.setStyleSheet(f"QPushButton {{ background: {color}; color: {fg}; "
                        f"border: 1px solid #cbd5e1; border-radius: 6px; "
                        f"padding: 8px 14px; font-weight: 600; }}")
        return b

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === Левая панель фильтров ===
        fscroll = QScrollArea()
        fscroll.setWidgetResizable(True)
        fscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        fscroll.setMinimumWidth(250)
        fscroll.setMaximumWidth(300)
        fw = QWidget()
        fl = QVBoxLayout(fw)
        fscroll.setWidget(fw)
        fscroll.setVisible(False)
        splitter.addWidget(fscroll)

        fl.addWidget(QLabel("Поиск:"))
        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("ФИО, телефон, email…")
        self.edit_filter.textChanged.connect(self._debounced_filter)
        fl.addWidget(self.edit_filter)

        fl.addWidget(QLabel("Статус:"))
        self.cb_status = QComboBox()
        for label, code in [("Все", None), ("Активен", "ACTIVE"), ("Заморожен", "FROZEN"),
                            ("Должник", "DEBTOR"), ("Архив", "ARCHIVED")]:
            self.cb_status.addItem(label, code)
        self.cb_status.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.cb_status)

        fl.addWidget(QLabel("Тип подписки:"))
        self.cb_subtype = QComboBox()
        for label, code in [("Все", None), ("Членство", "membership"),
                            ("Пакет", "pack"), ("Безлимит", "unlimited")]:
            self.cb_subtype.addItem(label, code)
        self.cb_subtype.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.cb_subtype)

        fl.addWidget(QLabel("Тег/сегмент:"))
        self.cb_tag = QComboBox()
        self.cb_tag.addItem("Все (⏳ в разработке)", None)
        fl.addWidget(self.cb_tag)

        fl.addWidget(QLabel("Источник:"))
        self.cb_source = QComboBox()
        self.cb_source.addItem("Все (⏳ в разработке)", None)
        fl.addWidget(self.cb_source)

        fl.addWidget(QLabel("Пол:"))
        self.cb_gender = QComboBox()
        for label, code in [("Все", None), ("Мужской", "MALE"), ("Женский", "FEMALE"),
                            ("Не указан", "НЕ_УКАЗАН")]:
            self.cb_gender.addItem(label, code)
        self.cb_gender.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.cb_gender)

        age_row = QHBoxLayout()
        age_row.addWidget(QLabel("Возраст:"))
        self.sp_age_from = QSpinBox(); self.sp_age_from.setRange(0, 120); self.sp_age_from.setSpecialValueText("—")
        self.sp_age_to = QSpinBox(); self.sp_age_to.setRange(0, 120); self.sp_age_to.setSpecialValueText("—")
        age_row.addWidget(self.sp_age_from)
        age_row.addWidget(self.sp_age_to)
        fl.addLayout(age_row)
        self.sp_age_from.valueChanged.connect(self._apply_filters)
        self.sp_age_to.valueChanged.connect(self._apply_filters)

        self.chk_no_visit = QCheckBox("Не приходил с:")
        self.chk_no_visit.setToolTip("Требует серверного фильтра — скоро")
        self.dt_no_visit = QDateEdit(QDate.currentDate().addDays(-30))
        self.dt_no_visit.setCalendarPopup(True)
        self.dt_no_visit.setEnabled(False)
        self.chk_no_visit.toggled.connect(self.dt_no_visit.setEnabled)
        fl.addWidget(self.chk_no_visit)
        fl.addWidget(self.dt_no_visit)

        self.sp_visits_lt = QSpinBox()
        self.sp_visits_lt.setRange(0, 999)
        self.sp_visits_lt.setSpecialValueText("—")
        self.sp_visits_lt.setPrefix("Визитов менее: ")
        self.sp_visits_lt.setToolTip("Требует серверного фильтра — скоро")
        fl.addWidget(self.sp_visits_lt)

        self.chk_tasks = QCheckBox("Только с открытыми задачами")
        self.chk_tasks.setToolTip("Требует серверного фильтра — скоро")
        fl.addWidget(self.chk_tasks)

        fl.addWidget(QLabel("Менеджер:"))
        self.cb_manager = QComboBox()
        self.cb_manager.addItem("Все", None)
        self.cb_manager.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.cb_manager)

        b_reset = self._btn("Сбросить фильтры")
        b_reset.clicked.connect(self._reset_filters)
        fl.addWidget(b_reset)

        b_adv = QToolButton()
        b_adv.setText("Расширенные фильтры ▼")
        b_adv.setStyleSheet("QToolButton { background: #f1f5f9; color: #475569; "
                            "border: 1px solid #cbd5e1; border-radius: 6px; "
                            "padding: 6px 10px; font-weight: 600; }")
        b_adv.clicked.connect(lambda: QMessageBox.information(
            self, "Фильтры", "Расширенные фильтры (возраст, визиты, задачи) —\n"
                             "после появления эндпоинта GET /clients?... на сервере."))
        fl.addWidget(b_adv)
        fl.addStretch(1)

        # === Правая часть: тулбар + таблица + экспорт ===
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(right)

        row = QHBoxLayout()
        self._btn_filters = QToolButton()
        self._btn_filters.setText(" Фильтры ▾")
        self._btn_filters.setCheckable(True)
        self._btn_filters.setStyleSheet("QToolButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        self._btn_filters.toggled.connect(lambda on: (fscroll.setVisible(on), self._btn_filters.setText(" Фильтры ▴" if on else " Фильтры ▾")))
        row.addWidget(self._btn_filters)
        row.addStretch()
        b_add = self._btn(" Добавить", "#10b981", "white"); b_add.clicked.connect(self._add)
        b_edit = self._btn(" Изменить", "#3b82f6", "white"); b_edit.clicked.connect(self._edit)
        b_deact = self._btn(" Деактивировать", "#fee2e2", "#b91c1c"); b_deact.clicked.connect(self._deactivate)
        b_del = self._btn(" Удалить", "#dc2626", "white"); b_del.clicked.connect(self._delete)
        b_ref = self._btn("Обновить"); b_ref.clicked.connect(self.refresh)
        for b in (b_add, b_edit, b_deact, b_del, b_ref):
            row.addWidget(b)
        rl.addLayout(row)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["ФИО", "Телефон", "Email", "Категория", "Статус", "Создан", "Баланс", "Бонусы"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        self.table.doubleClicked.connect(self._open_card)
        rl.addWidget(self.table, 1)

        # Панель экспорта
        hb = QHBoxLayout()
        hb.addStretch()
        for fmt, label in [("xlsx", "XLSX"), ("pdf", "PDF"), ("csv", "CSV"), ("json", "JSON"), ("1c", "1С")]:
            b = QPushButton(label)
            b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; "
                            "border: 1px solid #cbd5e1; border-radius: 6px; "
                            "padding: 6px 12px; font-weight: 600; }")
            b.clicked.connect(lambda _, f=fmt: self._export(f))
            hb.addWidget(b)
        rl.addLayout(hb)

        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._apply_filters)

    def _debounced_filter(self, _text):
        self._debounce.start()

    # ---------- Данные ----------
    def refresh(self):
        self.worker = ClientsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _fio(self, c):
        return " ".join(x for x in (c.get("last_name"), c.get("first_name"), c.get("middle_name")) if x) or "—"

    def _on_loaded(self, clients, subs, users):
        self._all_data = clients or []
        self._subs = subs or []
        self._users = users or []
        # менеджеры в фильтр
        cur = self.cb_manager.currentData()
        self.cb_manager.blockSignals(True)
        self.cb_manager.clear()
        self.cb_manager.addItem("Все", None)
        for u in self._users:
            roles = [str(r.get("code", "")).lower() for r in (u.get("roles") or []) if isinstance(r, dict)]
            if "manager" in roles:
                self.cb_manager.addItem(u.get("full_name") or u.get("username") or "—", str(u.get("id")))
        idx = self.cb_manager.findData(cur)
        if idx >= 0:
            self.cb_manager.setCurrentIndex(idx)
        self.cb_manager.blockSignals(False)
        self._apply_filters()

    def _subs_of(self, cid):
        return [s for s in self._subs if str(s.get("client_id")) == str(cid)]

    def _apply_filters(self):
        rows = list(self._all_data)
        # поиск
        t = self.edit_filter.text().strip().lower()
        if t:
            rows = [c for c in rows
                    if t in f"{self._fio(c)} {c.get('phone', '')} {c.get('email', '')}".lower()]
        # статус
        st = self.cb_status.currentData()
        if st:
            rows = [c for c in rows if str(c.get("status") or "").upper() == st]
        # пол
        g = self.cb_gender.currentData()
        if g:
            rows = [c for c in rows if str(c.get("gender") or "НЕ_УКАЗАН").upper() == g]
        # тип подписки
        sub_t = self.cb_subtype.currentData()
        if sub_t:
            def _match(c):
                subs = self._subs_of(c.get("id"))
                if sub_t == "unlimited":
                    return any(s.get("is_unlimited") for s in subs)
                if sub_t == "pack":
                    return any(s.get("visit_limit") and not s.get("is_unlimited") for s in subs)
                if sub_t == "membership":
                    return any(not s.get("is_unlimited") and not s.get("visit_limit") for s in subs)
                return True
            rows = [c for c in rows if _match(c)]
        # менеджер (если поле есть в карточке клиента)
        mgr = self.cb_manager.currentData()
        if mgr and any("manager_id" in c for c in self._all_data):
            rows = [c for c in rows if str(c.get("manager_id")) == str(mgr)]
        # возраст
        from datetime import datetime as _dt
        af, at = self.sp_age_from.value(), self.sp_age_to.value()
        if af or at:
            def _age_ok(c):
                bd = str(c.get("birth_date") or "")[:10]
                if not bd:
                    return not (af or at)
                try:
                    age = _dt.now().year - _dt.fromisoformat(bd).year
                except Exception:
                    return False
                if af and age < af:
                    return False
                if at and age > at:
                    return False
                return True
            rows = [c for c in rows if _age_ok(c)]
        self._render(rows)

    def _reset_filters(self):
        self.edit_filter.clear()
        self.cb_status.setCurrentIndex(0)
        self.cb_subtype.setCurrentIndex(0)
        self.cb_gender.setCurrentIndex(0)
        self.cb_manager.setCurrentIndex(0)
        self.sp_age_from.setValue(0)
        self.sp_age_to.setValue(0)
        self.sp_visits_lt.setValue(0)
        self.chk_no_visit.setChecked(False)
        self.chk_tasks.setChecked(False)
        self._apply_filters()

    def _render(self, rows):
        self.table.setRowCount(len(rows))
        for i, c in enumerate(rows):
            item0 = QTableWidgetItem(self._fio(c))
            item0.setData(Qt.ItemDataRole.UserRole, str(c.get("id")))
            self.table.setItem(i, 0, item0)
            self.table.setItem(i, 1, QTableWidgetItem(str(c.get("phone") or "—")))
            self.table.setItem(i, 2, QTableWidgetItem(str(c.get("email") or "—")))
            self.table.setItem(i, 3, QTableWidgetItem(
                CAT_LABELS.get(str(c.get("client_category") or ""), str(c.get("client_category") or "—"))))
            status = str(c.get("status") or "").upper()
            if c.get("is_active") is False and status == "ACTIVE":
                status = "INACTIVE"
            s_item = QTableWidgetItem(STATUS_LABELS.get(status, status or "—"))
            color = {"ACTIVE": "#059669", "FROZEN": "#3b82f6", "DEBTOR": "#d97706",
                     "ARCHIVED": "#64748b", "INACTIVE": "#ef4444"}.get(status, "#0f172a")
            s_item.setForeground(QColor(color))
            self.table.setItem(i, 4, s_item)
            self.table.setItem(i, 5, QTableWidgetItem(str(c.get("created_at") or "")[:10]))
            wb = c.get("wallet_balance")
            self.table.setItem(i, 6, QTableWidgetItem(
                ("%s ₽" % wb) if wb is not None else "—"))
            bn = c.get("bonuses")
            self.table.setItem(i, 7, QTableWidgetItem(str(bn) if bn is not None else "—"))

    # ---------- Действия ----------
    def _selected_client(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выбор", "Сначала выберите клиента в таблице")
            return None
        cid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for c in self._all_data:
            if str(c.get("id")) == cid:
                return c
        return None

    def _open_card(self, _idx=None):
        c = self._selected_client()
        if not c:
            return
        from windows.client_card import ClientCard
        dlg = ClientCard(self.api, str(c.get("id")), user_data={}, parent=None)
        dlg.show()

    def _add(self):
        dlg = FormDialog("Новый клиент", CLIENT_FIELDS, self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = _norm_gender(dlg.values())
        if not v.get("first_name") or not v.get("last_name") or not v.get("phone") or not v.get("email"):
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля: фамилия, имя, телефон, email")
            return
        payload = {k: val for k, val in v.items() if val not in ("", None)}
        if not _norm_birth_date(payload, self):
            return
        try:
            self.api.create_client(payload)
            self.refresh()
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.critical(self, "Ошибка создания", str(e)[:300])

    def _edit(self):
        c = self._selected_client()
        if not c:
            return
        fields = [
            ("last_name", "Фамилия *", "text", c.get("last_name")),
            ("first_name", "Имя *", "text", c.get("first_name")),
            ("middle_name", "Отчество", "text", c.get("middle_name")),
            ("phone", "Телефон *", "text", c.get("phone")),
            ("email", "Email *", "text", c.get("email")),
            ("gender", "Пол", "combo", [("Мужской", "MALE"), ("Женский", "FEMALE"), ("Не указан", "НЕ_УКАЗАН")]),
            ("birth_date", "Дата рождения (ДД-ММ-ГГГГ)", "text", _fmt_date(c.get("birth_date"))),
        ]
        dlg = FormDialog(f"Клиент: {self._fio(c)}", fields, self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = _norm_gender({k: val for k, val in dlg.values().items() if val not in ("", None)})
        if not _norm_birth_date(v, self):
            return
        try:
            self.api.update_client(str(c["id"]), v)
            self.refresh()
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:300])

    def _deactivate(self):
        c = self._selected_client()
        if not c:
            return
        if QMessageBox.question(self, "Деактивация",
                                f"Деактивировать клиента {self._fio(c)}?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api.update_client(str(c["id"]), {"is_active": False, "status": "INACTIVE"})
            self.refresh()
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:300])

    def _delete(self):
        c = self._selected_client()
        if not c:
            return
        if QMessageBox.warning(
                self, "Удаление клиента",
                f"УДАЛИТЬ клиента {self._fio(c)} безвозвратно?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api.delete_client(str(c["id"]))
            self.refresh()
        except (RuntimeError, _requests.HTTPError) as e:
            s = str(e)
            if "409" in s or "Conflict" in s:
                # FK-связи: предложить деактивацию
                if QMessageBox.question(
                        self, "Удаление невозможно",
                        "У клиента есть абонементы/связанные данные.\n"
                        "Деактивировать вместо удаления?") == QMessageBox.StandardButton.Yes:
                    try:
                        self.api.update_client(str(c["id"]), {"is_active": False, "status": "INACTIVE"})
                        self.refresh()
                    except (RuntimeError, _requests.HTTPError) as e2:
                        QMessageBox.critical(self, "Ошибка", str(e2)[:300])
            else:
                QMessageBox.critical(self, "Ошибка удаления", s[:300])

    def _export(self, fmt):
        from windows.export_helper import (export_table_xlsx, export_table_pdf,
                                           export_counterparties_1c)
        try:
            if fmt == "1c":
                rows = self._visible_clients()
                export_counterparties_1c(self, rows)
                return
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            rows = [[self.table.item(r, c).text() if self.table.item(r, c) else ""
                     for c in range(self.table.columnCount())] for r in range(self.table.rowCount())]
            if fmt == "xlsx":
                export_table_xlsx(self, headers, rows, "clients", "Клиенты")
            elif fmt == "pdf":
                export_table_pdf(self, headers, rows, "clients", "Клиенты")
            elif fmt == "csv":
                from windows.export_helper import _write_csv
                _write_csv(self, headers, rows, "Клиенты")
            elif fmt == "json":
                from windows.export_helper import _write_json
                _write_json(self, headers, rows, "Клиенты")
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.warning(self, "Экспорт", str(e)[:200])

    def _visible_clients(self):
        ids = set()
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it:
                cid = it.data(Qt.ItemDataRole.UserRole)
                if cid:
                    ids.add(str(cid))
        return [c for c in self._all_data if str(c.get("id")) in ids]

    def _on_error(self, msg):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))