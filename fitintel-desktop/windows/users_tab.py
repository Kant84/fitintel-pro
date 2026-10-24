# -*- coding: utf-8 -*-
"""FitIntel Pro — Users Tab: CRUD + фильтры (поиск/отдел/роль/статус) + карточка сотрудника."""
import requests as _requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox,
    QSplitter, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QMessageBox, QAbstractItemView, QToolButton, QInputDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog
from app_logging import log


class UsersWorker(QThread):
    finished = pyqtSignal(object)
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
        self._departments = []
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
        rowd = QHBoxLayout()
        self.cb_dept = QComboBox()
        self.cb_dept.setEditable(True)
        self.cb_dept.setToolTip("Выберите из списка или введите новый —\nсоздание при сохранении пользователя")
        self.cb_dept.addItem("Все", None)
        self.cb_dept.currentTextChanged.connect(self._apply_filters)
        rowd.addWidget(self.cb_dept, 1)
        b_newd = QToolButton()
        b_newd.setText("＋")
        b_newd.setToolTip("Создать отдел")
        b_newd.clicked.connect(self._new_department)
        rowd.addWidget(b_newd)
        fl.addLayout(rowd)

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
        self._btn_filters.setText(" Поиск ▾")
        self._btn_filters.setCheckable(True)
        self._btn_filters.setStyleSheet("QToolButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding:8px 14px; font-weight: 600; }")
        self._btn_filters.toggled.connect(lambda on: (fscroll.setVisible(on), self._btn_filters.setText(" Поиск ▴" if on else " Поиск ▾")))
        row.addWidget(self._btn_filters)
        row.addStretch()
        b_add = self._btn("Создать пользователя", "#10b981", "white")
        b_add.clicked.connect(self._add)
        b_edit = self._btn(" Изменить", "#3b82f6", "white")
        b_edit.clicked.connect(self._edit_user)
        b_edit.setVisible(False)  # редактирование — в карточке сотрудника
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
        # === USER TRASH BUTTON ===
        b_trash = self._btn("Корзина")
        b_trash.clicked.connect(
            lambda _c: __import__(
                "windows.trash_dialog",
                fromlist=["TrashDialog"],
            ).TrashDialog(self.api, self).exec()
        )
        b_ref = self._btn("Обновить")
        b_ref.clicked.connect(self.refresh)
        for b in (b_add, b_edit, b_del, self.chk_show_deleted, b_trash, b_ref):
            row.addWidget(b)
        rl.addLayout(row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ФИО", "Логин", "Email", "Роли", "Отдел", "Прав", "Статус"])
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

    # ---------- Отделы ----------
    def _load_departments(self):
        deps = []
        try:
            r = self.api.session.get(self.api._url("/analytics/departments"), timeout=15)
            r.raise_for_status()
            deps = list(r.json().get("items", []))
        except Exception:
            pass
        for u in self._all_users or []:
            d = (u.get("department") or "").strip()
            if d and d not in deps:
                deps.append(d)
        self._departments = sorted(deps)

    def _refill_dept_combo(self):
        cur = self.cb_dept.currentText()
        self.cb_dept.blockSignals(True)
        self.cb_dept.clear()
        self.cb_dept.addItem("Все", None)
        for d in self._departments:
            self.cb_dept.addItem(d)
        if cur and cur != "Все":
            self.cb_dept.setCurrentText(cur)
        self.cb_dept.blockSignals(False)

    def _new_department(self):
        name, ok = QInputDialog.getText(self, "Новый отдел", "Название отдела:")
        name = (name or "").strip()
        if not ok or not name:
            return
        try:
            self.api.session.post(self.api._url("/analytics/departments"),
                                  json={"name": name}, timeout=15)
        except Exception as e:
            QMessageBox.warning(self, "Отдел", "Не удалось создать: %s" % str(e)[:150])
        self._load_departments()
        self._refill_dept_combo()
        self.cb_dept.setCurrentText(name)
        self._apply_filters()

    def _save_department_for(self, uid, name):
        """Сохранить отдел пользователю; новый отдел создаётся автоматически."""
        name = (name or "").strip()
        if not name or not uid:
            return
        try:
            self.api.session.post(self.api._url("/analytics/departments"),
                                  json={"name": name}, timeout=15)
        except Exception:
            pass
        try:
            self.api.session.post(self.api._url("/users/%s/department" % uid),
                                  json={"department": name}, timeout=15)
        except Exception as e:
            QMessageBox.warning(self, "Отдел", "Отдел не сохранён: %s" % str(e)[:150])

    # ---------- Данные ----------
    def refresh(self):
        self.worker = UsersWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, users):
        if isinstance(users, dict):
            users = users.get("items") or users.get("users") or []
        self._all_users = users or []
        # отделы
        self._load_departments()
        self._refill_dept_combo()
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

    def _current_department_filter(self):
        # редактируемый комбо: выбранный текст (кроме «Все»)
        t = self.cb_dept.currentText().strip()
        return None if t in ("", "Все") else t

    def _apply_filters(self):
        users = list(self._all_users or [])
        show_del = self.chk_show_deleted.isChecked()
        if not show_del:
            users = [u for u in users if isinstance(u, dict)]
            users = [u for u in users
                     if not (str(u.get("username") or "").startswith("deleted_")
                             and not u.get("is_active"))]
        t = self.edit_filter.text().strip().lower()
        if t:
            users = [u for u in users if isinstance(u, dict) and t in "%s %s %s" % (
                (u.get("full_name") or ""), u.get("username", ""), u.get("email", "")).lower()]
        dept = self.cb_dept.currentText().strip()
        if dept and dept != "Все":
            users = [u for u in users if isinstance(u, dict)
                     and (u.get("department") or "") == dept]
        role = self.cb_role.currentData()
        if role:
            users = [u for u in users if isinstance(u, dict)
                     and any(str(r.get("code", "")).lower() == role
                             for r in (u.get("roles") or []) if isinstance(r, dict))]
        st = self.cb_status.currentData()
        if st == "active":
            users = [u for u in users if isinstance(u, dict) and u.get("is_active")]
        elif st == "inactive":
            users = [u for u in users if isinstance(u, dict) and not u.get("is_active")]
        print("users_tab: loaded=%d shown=%d" % (len(self._all_users or []), len(users)))
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            try:
                if not isinstance(u, dict):
                    print("users_tab: bad item at", i, type(u).__name__)
                    continue
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
                self.table.setItem(i, 4, QTableWidgetItem(str(u.get("department") or "—")))
                perms = u.get("permissions") or []
                self.table.setItem(i, 5, QTableWidgetItem(str(len(perms)) if isinstance(perms, list) else "—"))
                active = u.get("is_active")
                item = QTableWidgetItem("Активен" if active else "Отключён")
                item.setForeground(QColor("#059669" if active else "#ef4444"))
                self.table.setItem(i, 6, item)
            except Exception as _rowe:
                print("users_tab: row %d error: %s" % (i, str(_rowe)[:120]))
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
        self._open_cards = getattr(self, "_open_cards", [])
        self._open_cards.append(dlg)
        dlg.destroyed.connect(lambda _=None, d=dlg: self._open_cards.remove(d) if d in self._open_cards else None)
        dlg.show()

    def _user_by_id(self, uid):
        for u in self._all_users or []:
            if str(u.get("id") or "") == str(uid):
                return u
        return {}

    # ---------- CRUD ----------
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
            ("department", "Отдел (новый создастся автоматически)"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        ROLE_DEPT = {"trainer": "Тренеры", "accountant": "Бухгалтерия",
                     "reception": "Ресепшен", "cashier": "Ресепшен",
                     "manager": "Администрация", "admin": "Администрация",
                     "support": "Поддержка", "owner": "Руководство"}
        if not (v.get("department") or "").strip():
            v["department"] = ROLE_DEPT.get(str(v.get("role") or ""), "")
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
            if uid:
                self._save_department_for(uid, v.get("department"))
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
        cur = self._user_by_id(uid)
        dlg = FormDialog("Пользователь: " + login, [
            ("full_name", "ФИО (имя для клиентов)", "text", cur.get("full_name") or ""),
            ("email", "Email", "text", cur.get("email") or ""),
            ("department", "Отдел (новый создастся автоматически)", "text", cur.get("department") or ""),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val not in (None, "")}
        if not v:
            return
        try:
            base = {k: v[k] for k in ("full_name", "email") if k in v}
            if base:
                r = self.api.session.patch(self.api._url(f"/users/{uid}"), json=base)
                r.raise_for_status()
            if "department" in v:
                self._save_department_for(uid, v["department"])
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
