# -*- coding: utf-8 -*-
"""FitIntel Pro — Users Tab: CRUD + фильтры + карточка сотрудника (двойной клик)."""
import requests as _requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox,
    QSplitter, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QMessageBox, QAbstractItemView, QToolButton)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog
from app_logging import log


class UsersWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            self.finished.emit(self.api.get_users())
        except Exception as e:
            self.error.emit(str(e))


class UsersTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._all_users = []
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
        self.edit_filter.setPlaceholderText("ФИО, логин, email…")
        self.edit_filter.textChanged.connect(self._debounced_filter)
        fl.addWidget(self.edit_filter)

        fl.addWidget(QLabel("Отдел:"))
        self.cb_dept = QComboBox()
        self.cb_dept.addItem("Все (⏳ в разработке)", None)
        fl.addWidget(self.cb_dept)

        fl.addWidget(QLabel("Роль:"))
        self.cb_role = QComboBox()
        self.cb_role.addItem("Все", None)
        self.cb_role.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.cb_role)

        fl.addWidget(QLabel("Статус:"))
        self.cb_status = QComboBox()
        self.cb_status.addItem("Все", None)
        self.cb_status.addItem("Активен", "active")
        self.cb_status.addItem("Отключён", "inactive")
        self.cb_status.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.cb_status)
        fl.addStretch(1)

        # === Правая часть ===
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
        b_add = self._btn("Создать пользователя", "#10b981", "white")
        b_add.clicked.connect(self._add)
        b_edit = self._btn(" Изменить", "#3b82f6", "white")
        b_edit.clicked.connect(self._edit_user)
        b_del = self._btn("Удалить", "#fef2f2", "#b91c1c")
        b_del.setStyleSheet("QPushButton { background: #fef2f2; border: 1px solid #fca5a5; "
                            "color: #b91c1c; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_del.clicked.connect(self._delete)
        self.chk_show_deleted = QPushButton("Показать удалённых")
        self.chk_show_deleted.setCheckable(True)
        self.chk_show_deleted.setStyleSheet("QPushButton { background: #f1f5f9; "
                                            "border: 1px solid #cbd5e1; border-radius: 6px; "
                                            "padding: 8px 14px; font-weight: 600; }")
        self.chk_show_deleted.toggled.connect(lambda _c: self._apply_filters())
        b_ref = self._btn("Обновить")
        b_ref.clicked.connect(self.refresh)
        for b in (b_add, b_edit, b_del, self.chk_show_deleted, b_ref):
            row.addWidget(b)
        rl.addLayout(row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ФИО", "Логин", "Email", "Роли", "Прав", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        self.table.doubleClicked.connect(self._open_card)
        rl.addWidget(self.table, 1)

        hb = QHBoxLayout()
        hb.addStretch()
        from windows.export_helper import make_save_menu_button
        hb.addWidget(make_save_menu_button(self, self._export))
        rl.addLayout(hb)

        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._apply_filters)

    def _debounced_filter(self, _t):
        self._debounce.start()

    # ---------- Данные ----------
    def refresh(self):
        self.worker = UsersWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, users):
        self._all_users = users or []
        # роли в фильтр
        roles = self._load_roles()
        cur = self.cb_role.currentData()
        self.cb_role.blockSignals(True)
        self.cb_role.clear()
        self.cb_role.addItem("Все", None)
        for label, code in roles:
            self.cb_role.addItem(label, code)
        idx = self.cb_role.findData(cur)
        if idx >= 0:
            self.cb_role.setCurrentIndex(idx)
        self.cb_role.blockSignals(False)
        self._apply_filters()

    def _apply_filters(self):
        users = list(self._all_users)
        show_del = self.chk_show_deleted.isChecked()
        if not show_del:
            users = [u for u in users
                     if not (str(u.get("username") or "").startswith("deleted_")
                             and not u.get("is_active"))]
        t = self.edit_filter.text().strip().lower()
        if t:
            users = [u for u in users if t in "%s %s %s" % (
                (u.get("full_name") or ""), u.get("username", ""), u.get("email", "")).lower()]
        role = self.cb_role.currentData()
        if role:
            users = [u for u in users
                     if any(str(r.get("code", "")).lower() == role
                            for r in (u.get("roles") or []) if isinstance(r, dict))]
        st = self.cb_status.currentData()
        if st == "active":
            users = [u for u in users if u.get("is_active")]
        elif st == "inactive":
            users = [u for u in users if not u.get("is_active")]
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            _fn = (u.get("full_name") or "").strip()
            self.table.setItem(i, 0, QTableWidgetItem(_fn or "—"))
            item0 = QTableWidgetItem(str(u.get("username") or "—"))
            item0.setData(Qt.ItemDataRole.UserRole, str(u.get("id") or ""))
            self.table.setItem(i, 1, item0)
            self.table.setItem(i, 2, QTableWidgetItem(str(u.get("email") or "—")))
            roles = u.get("roles") or []
            if isinstance(roles, list):
                rtxt = ", ".join(str(r.get("name", r)) if isinstance(r, dict) else str(r) for r in roles)
            else:
                rtxt = str(roles)
            self.table.setItem(i, 3, QTableWidgetItem(rtxt or "—"))
            perms = u.get("permissions") or []
            self.table.setItem(i, 4, QTableWidgetItem(str(len(perms)) if isinstance(perms, list) else "—"))
            active = u.get("is_active")
            item = QTableWidgetItem("Активен" if active else "Отключён")
            item.setForeground(QColor("#059669" if active else "#ef4444"))
            self.table.setItem(i, 5, item)

    # ---------- Карточка ----------
    def _open_card(self, _idx=None):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 1)
        uid = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not uid:
            return
        from windows.employee_card import EmployeeCard
        dlg = EmployeeCard(self.api, uid, user_data={}, parent=None)
        dlg.show()

    # ---------- CRUD (без изменений логики) ----------
    def _load_roles(self):
        try:
            resp = self.api.session.get(self.api._url("/rbac/roles-matrix"))
            resp.raise_for_status()
            body = resp.json()
            rows = body.get("roles", body) if isinstance(body, dict) else body
            skip = {"client", "device", "superadmin"}
            labels = {"admin": "Администратор", "manager": "Менеджер",
                      "trainer": "Тренер", "reception": "Ресепшен",
                      "cashier": "Кассир", "accountant": "Бухгалтер",
                      "support": "Поддержка", "owner": "Владелец"}
            out = []
            for r in rows if isinstance(rows, list) else []:
                code = str(r.get("role_code") or r.get("code") or "").lower()
                if not code or code in skip:
                    continue
                name = labels.get(code, r.get("role_name") or code)
                out.append((name, code))
            if out:
                return out
        except Exception:
            pass
        return [("Менеджер", "manager"), ("Тренер", "trainer"),
                ("Ресепшен", "reception"), ("Администратор", "admin")]

    def _add(self):
        dlg = FormDialog("Новый пользователь", [
            ("username", "Логин *"),
            ("full_name", "ФИО (видят клиенты в приложении)"),
            ("email", "Email *"),
            ("password", "Пароль * (мин. 6 символов)"),
            ("role", "Роль *", "combo", self._load_roles()),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["username"] or not v["password"]:
            QMessageBox.warning(self, "Ошибка", "Логин и пароль обязательны")
            return
        try:
            payload = {"username": v["username"], "email": v["email"], "password": v["password"]}
            if v.get("full_name"):
                payload["full_name"] = v["full_name"]
            r = self.api.session.post(self.api._url("/users/"), json=payload)
            r.raise_for_status()
            uid = r.json().get("id")
            if uid and v.get("role"):
                r2 = self.api.session.post(self.api._url(f"/users/{uid}/roles/assign"),
                                           json={"role_code": v["role"]})
                r2.raise_for_status()
            self.refresh()
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.critical(self, "Ошибка создания", str(e)[:300])

    def _edit_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Изменение", "Выберите пользователя в таблице")
            return
        item = self.table.item(row, 1)
        uid = item.data(Qt.ItemDataRole.UserRole) if item else None
        login = item.text() if item else "?"
        if not uid:
            QMessageBox.warning(self, "Изменение", "ID не найден — нажмите «Обновить»")
            return
        dlg = FormDialog("Пользователь: " + login, [
            ("full_name", "ФИО (имя для клиентов)"),
            ("email", "Email"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val}
        if not v:
            return
        try:
            r = self.api.session.patch(self.api._url(f"/users/{uid}"), json=v)
            r.raise_for_status()
            self.refresh()
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:300])

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Удаление", "Сначала выберите пользователя в таблице")
            return
        item = self.table.item(row, 1)
        uid = item.data(Qt.ItemDataRole.UserRole) if item else None
        login = item.text() if item else "?"
        if not uid:
            QMessageBox.warning(self, "Удаление", "ID пользователя не найден — нажмите «Обновить»")
            return
        if login.lower() == "superadmin":
            QMessageBox.warning(self, "Удаление", "superadmin нельзя удалить")
            return
        if QMessageBox.question(
                self, "Удаление пользователя",
                f"Удалить пользователя «{login}» безвозвратно?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            r = self.api.session.delete(self.api._url(f"/users/{uid}"))
            r.raise_for_status()
            self.refresh()
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e)[:300])

    def _export(self, fmt):
        from windows.export_helper import export_table_xlsx, export_table_pdf
        try:
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            rows = [[self.table.item(r, c).text() if self.table.item(r, c) else ""
                     for c in range(self.table.columnCount())] for r in range(self.table.rowCount())]
            from windows.export_helper import _save_one
            _save_one(self, fmt, headers, rows, "Пользователи")
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.warning(self, "Экспорт", str(e)[:200])

    def _on_error(self, msg):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))


# === E63_PRINT ===
try:
    from windows.print_helper import add_print_button as _e63_apb
    _e63_orig = UsersTab.__init__
    def _e63_init(self, *a, **kw):
        _e63_orig(self, *a, **kw)
        try:
            _e63_apb(self, "Пользователи")
        except Exception as e:
            print("print btn:", e)
    UsersTab.__init__ = _e63_init
    print("E63 print OK: users_tab.py")
except Exception as e:
    print("E63 FAIL:", e)

# === скрыть лишнюю кнопку «В PDF» (E63) ===
try:
    import inspect as _i
    from PyQt6.QtWidgets import QWidget as _W, QPushButton as _PB
    for _n, _o in list(globals().items()):
        if (_i.isclass(_o) and issubclass(_o, _W)
                and getattr(_o, "__module__", "") == __name__ and not _n.startswith("_")):
            _oi = _o.__init__
            def _mk(orig):
                def _ii(self, *a, **k):
                    orig(self, *a, **k)
                    try:
                        for b in self.findChildren(_PB):
                            if "PDF" in b.text() and "Сохранить" not in b.text():
                                b.setVisible(False)
                    except Exception:
                        pass
                return _ii
            _o.__init__ = _mk(_oi)
    print("PDF cleanup OK: users_tab")
except Exception as _e:
    print("PDF cleanup FAIL:", _e)

# === W10: скрыть фильтр «Отдел (в разработке)» до появления данных ===
try:
    _orig_init_ut_w10 = UsersTab.__init__
    def _init_ut_w10(self, *a, **k):
        _orig_init_ut_w10(self, *a, **k)
        from PyQt6.QtWidgets import QComboBox as _CB, QLabel as _LB
        for cb in self.findChildren(_CB):
            for i in range(cb.count()):
                if "разработке" in cb.itemText(i):
                    for l in self.findChildren(_LB):
                        if l.text().strip().startswith("Отдел"):
                            l.setVisible(False)
                            break
                    cb.setVisible(False)
                    break
    UsersTab.__init__ = _init_ut_w10
    print("users: dept filter hidden")
except Exception as _e10u:
    print("users dept patch FAIL:", _e10u)