from PyQt6.QtGui import QColor
# -*- coding: utf-8 -*-
"""Карточка сотрудника: личные данные / график / расписание / расчёт ЗП (заглушки)."""
import requests as _requests
import windows.theme as theme
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QScrollArea, QTabWidget, QWidget, QFormLayout, QListWidget,
    QCalendarWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QLineEdit, QDoubleSpinBox, QGroupBox, QGridLayout, QInputDialog,
    QAbstractItemView)
from windows.icons import icon as _icon, polish as _polish
from app_logging import log


class EmployeeCard(QDialog):
    def __init__(self, api, user_id: str, user_data=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.user_id = str(user_id)
        self.user_data = user_data or {}
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Карточка сотрудника")
        self.resize(1100, 700)
        self._user = None
        self._build_ui()
        self._load()
        _polish(self)
        from windows.help_dialog import install_f1
        install_f1(self, "employee_card")

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(260)
        left_scroll.setMaximumWidth(320)
        self._left = QWidget()
        self._left_layout = QVBoxLayout(self._left)
        left_scroll.setWidget(self._left)
        splitter.addWidget(left_scroll)

        self._tabs = QTabWidget()
        splitter.addWidget(self._tabs)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setMinimumWidth(240)
        right_scroll.setMaximumWidth(300)
        self._right = QWidget()
        self._right_layout = QVBoxLayout(self._right)
        right_scroll.setWidget(self._right)
        splitter.addWidget(right_scroll)

        splitter.setStretchFactor(1, 1)
        main.addWidget(splitter, 1)

        self._t_main = self._add_tab("Личные данные")
        self._t_sched = self._add_tab("График работы")
        self._t_classes = self._add_tab("Расписание занятий")
        self._t_salary = self._add_tab("Расчёт ЗП")

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

    @staticmethod
    def _btn(text):
        b = QPushButton(text)
        b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; "
                        "border: 1px solid #cbd5e1; border-radius: 6px; "
                        "padding: 8px 14px; font-weight: 600; }")
        return b

    def _load(self):
        class _W(QThread):
            done = pyqtSignal(list)
            err = pyqtSignal(str)
            def __init__(self, api):
                super().__init__(); self.api = api
            def run(self):
                try:
                    self.done.emit(self.api.get_users())
                except Exception as e:
                    self.err.emit(str(e))
        self._w = _W(self.api)
        self._w.done.connect(self._on_users)
        self._w.err.connect(lambda m: QMessageBox.warning(self, "Ошибка", str(m)[:300]))
        self._w.start()

    def _on_users(self, users):
        self._user = next((u for u in (users or [])
                           if str(u.get("id")) == str(self.user_id)), None)
        if not self._user:
            QMessageBox.warning(self, "Ошибка", "Сотрудник не найден")
            self.close()
            return
        self._render_left()
        self._render_main()
        self._render_sched()
        self._render_classes()
        self._render_salary()
        self._render_right()

    def _fio(self):
        u = self._user or {}
        return (u.get("full_name") or "").strip() or u.get("username") or "—"

    def _render_left(self):
        while self._left_layout.count():
            it = self._left_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        avatar = QLabel(self._fio()[:2].upper())
        avatar.setFixedSize(180, 180)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("background: #3b82f6; color: white; font-size: 48px; border-radius: 90px;")
        self._left_layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        lbl = QLabel(self._fio())
        f = lbl.font(); f.setBold(True); f.setPointSize(14)
        lbl.setFont(f); lbl.setWordWrap(True)
        self._left_layout.addWidget(lbl)
        roles = ", ".join(str(r.get("name") or r.get("code") or "")
                          for r in (self._user.get("roles") or []) if isinstance(r, dict))
        self._left_layout.addWidget(QLabel(f"Роль: {roles or '—'}"))
        active = bool(self._user.get("is_active"))
        status = QLabel(f"Статус: {'Активен' if active else 'Отключён'}")
        status.setStyleSheet(f"color: {theme.ok_color() if active else theme.err_color()}; font-weight: 600;")
        self._left_layout.addWidget(status)
        b1 = self._btn("Открыть матрицу ролей")
        b1.clicked.connect(lambda: QMessageBox.information(self, "Роли", "Откройте экран Роли и права"))
        self._left_layout.addWidget(b1)
        b2 = self._btn("Сбросить пароль")
        b2.clicked.connect(lambda: QMessageBox.information(
            self, "Пароль", "Откройте экран Пользователи → Изменить"))
        self._left_layout.addWidget(b2)
        self._left_layout.addStretch(1)

    def _render_main(self):
        lay = self._t_main._layout
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        u = self._user or {}
        form = QFormLayout()
        form.addRow("Логин:", QLabel(str(u.get("username") or "—")))
        form.addRow("Email:", QLabel(str(u.get("email") or "—")))
        form.addRow("ФИО:", QLabel(str(u.get("full_name") or "—")))
        roles = [str(r.get("name") or r.get("code") or "")
                 for r in (u.get("roles") or []) if isinstance(r, dict)]
        lw = QListWidget()
        lw.addItems(roles or ["—"])
        form.addRow("Роли:", lw)
        perms = u.get("permissions") or []
        form.addRow("Прав:", QLabel(f"{len(perms)} шт." if isinstance(perms, list) else "—"))
        lay.addLayout(form)
        b = self._btn("Редактировать")
        b.clicked.connect(self._edit)
        lay.addWidget(b)
        lay.addStretch(1)

    def _edit(self):
        from windows.form_dialog import FormDialog
        dlg = FormDialog("Сотрудник: " + self._fio(), [
            ("full_name", "ФИО (имя для клиентов)", "text", (self._user or {}).get("full_name") or ""),
            ("email", "Email", "text", (self._user or {}).get("email") or ""),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val}
        if not v:
            return
        try:
            r = self.api.session.patch(self.api._url(f"/users/{self.user_id}"), json=v)
            r.raise_for_status()
            self._load()
        except (RuntimeError, _requests.HTTPError) as e:
            QMessageBox.warning(self, "Ошибка", str(e)[:300])

    def _render_sched(self):
        lay = self._t_sched._layout
        cal = QCalendarWidget()
        lay.addWidget(cal)
        lbl = QLabel("Данные из /schedules/ в разработке")
        lbl.setStyleSheet("color: #64748b;")
        lay.addWidget(lbl)
        lay.addStretch(1)

    def _render_classes(self):
        lay = self._t_classes._layout
        tbl = QTableWidget(0, 4)
        tbl.setHorizontalHeaderLabels(["Дата", "Занятие", "Зал", "Запись"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setStyleSheet(theme.table_style())
        lay.addWidget(tbl)
        lbl = QLabel("Расписание тренера — в разработке")
        lbl.setStyleSheet("color: #64748b;")
        lay.addWidget(lbl)
        lay.addStretch(1)

    def _render_salary(self):
        lay = self._t_salary._layout
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        form = QFormLayout()
        form.addRow("Оклад:", QLabel("—"))
        form.addRow("Ставка, ₽/ч:", QLabel("—"))
        form.addRow("Комиссия, %:", QLabel("—"))
        form.addRow("Итого:", QLabel("—"))
        lay.addLayout(form)
        lbl = QLabel("Расчёт зарплаты ведётся в разделе «Бухгалтерия → Зарплата»")
        lbl.setStyleSheet("color: #64748b;")
        lay.addWidget(lbl)
        lay.addStretch(1)

    def _render_right(self):
        while self._right_layout.count():
            it = self._right_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        created = str((self._user or {}).get("created_at") or "")[:10]
        if created:
            self._right_layout.addWidget(QLabel(f"Принят: {created}"))
        self._right_layout.addStretch(1)