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

        top = QHBoxLayout()
        top.addWidget(QLabel("Месяц:"))
        self._zp_month = QComboBox()
        now = QDate.currentDate()
        for i in range(12):
            d = now.addMonths(-i)
            self._zp_month.addItem(d.toString("MMMM yyyy"), d.toString("yyyy-MM"))
        self._zp_month.currentIndexChanged.connect(self._zp_load)
        top.addWidget(self._zp_month)
        b_calc = QPushButton(" Рассчитать")
        b_calc.setStyleSheet("background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_calc.clicked.connect(self._zp_load)
        top.addWidget(b_calc)
        top.addStretch()
        lay.addLayout(top)

        gb_pos = QGroupBox("Штатное расписание (должность → оклад ₽/мес)")
        gp = QGridLayout(gb_pos)
        self._zp_pos_tbl = QTableWidget(0, 2)
        self._zp_pos_tbl.setHorizontalHeaderLabels(["Должность", "Оклад"])
        self._zp_pos_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._zp_pos_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._zp_pos_tbl.setStyleSheet(theme.table_style())
        gp.addWidget(self._zp_pos_tbl, 0, 0, 1, 4)
        b_p_add = QPushButton(" Добавить")
        b_p_edit = QPushButton(" Изменить оклад")
        b_p_del = QPushButton(" Удалить")
        for b in (b_p_add, b_p_edit, b_p_del):
            b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; font-weight: 600; }")
        b_p_add.clicked.connect(self._zp_pos_add)
        b_p_edit.clicked.connect(self._zp_pos_edit)
        b_p_del.clicked.connect(self._zp_pos_del)
        gp.addWidget(b_p_add, 1, 1)
        gp.addWidget(b_p_edit, 1, 2)
        gp.addWidget(b_p_del, 1, 3)
        lay.addWidget(gb_pos)

        gb_me = QGroupBox("Параметры сотрудника")
        fm = QFormLayout(gb_me)
        self._zp_pos = QComboBox()
        fm.addRow("Должность:", self._zp_pos)
        self._zp_base = QLineEdit()
        self._zp_base.setPlaceholderText("пусто = оклад из штатного расписания")
        fm.addRow("Оклад (переопределение), ₽:", self._zp_base)
        self._zp_rate = QDoubleSpinBox()
        self._zp_rate.setMaximum(1000000)
        fm.addRow("Ставка, ₽/ч:", self._zp_rate)
        self._zp_comm = QDoubleSpinBox()
        self._zp_comm.setMaximum(100)
        fm.addRow("Комиссия, %:", self._zp_comm)
        b_save_me = QPushButton(" Сохранить параметры")
        b_save_me.setStyleSheet("background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_save_me.clicked.connect(self._zp_save_me)
        fm.addRow(b_save_me)
        lay.addWidget(gb_me)

        gb_acc = QGroupBox("Начисления за месяц")
        fa = QFormLayout(gb_acc)
        self._zp_adv = QDoubleSpinBox(); self._zp_adv.setMaximum(100000000)
        self._zp_ded = QDoubleSpinBox(); self._zp_ded.setMaximum(100000000)
        self._zp_fin = QDoubleSpinBox(); self._zp_fin.setMaximum(100000000)
        self._zp_bon = QDoubleSpinBox(); self._zp_bon.setMaximum(100000000)
        fa.addRow("Аванс, ₽:", self._zp_adv)
        fa.addRow("Удержания, ₽:", self._zp_ded)
        fa.addRow("Штрафы, ₽:", self._zp_fin)
        fa.addRow("Премия, ₽:", self._zp_bon)
        b_save_acc = QPushButton(" Сохранить начисления")
        b_save_acc.setStyleSheet("background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_save_acc.clicked.connect(self._zp_save_acc)
        fa.addRow(b_save_acc)
        lay.addWidget(gb_acc)

        self._zp_tbl = QTableWidget(0, 10)
        self._zp_tbl.setHorizontalHeaderLabels(
            ["Сотрудник", "Должность", "Оклад", "Начисления(сдельные)", "Комиссия %",
             "Комиссия", "Премия", "Аванс", "Удерж./Штрафы", "Итого"])
        self._zp_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._zp_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._zp_tbl.setAlternatingRowColors(True)
        self._zp_tbl.setStyleSheet(theme.table_style())
        lay.addWidget(self._zp_tbl, 1)

        self._zp_load_positions()
        self._zp_load_me()
        self._zp_load()

    def _zp_load_positions(self):
        try:
            data = self.api._e55_get("/staff/positions") or {}
            items = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        except Exception:
            items = []
        self._zp_positions = items
        cur = self._zp_pos.currentData() if hasattr(self, "_zp_pos") else None
        self._zp_pos.blockSignals(True)
        self._zp_pos.clear()
        self._zp_pos.addItem("— не указана —", None)
        for p in items:
            self._zp_pos.addItem(str(p.get("name")), p.get("id"))
        i = self._zp_pos.findData(cur)
        if i >= 0:
            self._zp_pos.setCurrentIndex(i)
        self._zp_pos.blockSignals(False)
        self._zp_pos_tbl.setRowCount(0)
        for p in items:
            r = self._zp_pos_tbl.rowCount()
            self._zp_pos_tbl.insertRow(r)
            it0 = QTableWidgetItem(str(p.get("name")))
            it0.setData(Qt.ItemDataRole.UserRole, str(p.get("id")))
            self._zp_pos_tbl.setItem(r, 0, it0)
            self._zp_pos_tbl.setItem(r, 1, QTableWidgetItem(str(p.get("base_salary"))))

    def _zp_pos_add(self):
        name, ok = QInputDialog.getText(self, "Должность", "Название:")
        if not ok or not name.strip():
            return
        sal, ok2 = QInputDialog.getDouble(self, "Должность", "Оклад ₽/мес:", 0, 0, 100000000, 2)
        if not ok2:
            return
        import time as _t
        try:
            self.api._e55_post("/staff/positions",
                               {"code": "pos_%d" % int(_t.time()), "name": name.strip(), "base_salary": sal})
            self._zp_load_positions()
        except Exception as e:
            QMessageBox.warning(self, "Штатка", str(e)[:200])

    def _zp_pos_edit(self):
        row = self._zp_pos_tbl.currentRow()
        if row < 0:
            return
        pid = self._zp_pos_tbl.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name = self._zp_pos_tbl.item(row, 0).text()
        sal, ok = QInputDialog.getDouble(self, "Должность", "Оклад ₽/мес для «%s»:" % name,
                                         float(self._zp_pos_tbl.item(row, 1).text() or 0), 0, 100000000, 2)
        if not ok:
            return
        try:
            self.api._e55_patch("/staff/positions/%s" % pid, {"base_salary": sal})
            self._zp_load_positions()
        except Exception as e:
            QMessageBox.warning(self, "Штатка", str(e)[:200])

    def _zp_pos_del(self):
        row = self._zp_pos_tbl.currentRow()
        if row < 0:
            return
        pid = self._zp_pos_tbl.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Штатка", "Удалить должность?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api._e55_del("/staff/positions/%s" % pid)
            self._zp_load_positions()
        except Exception as e:
            QMessageBox.warning(self, "Штатка", str(e)[:200])

    def _zp_load_me(self):
        try:
            d = self.api._e55_get("/staff/payroll/%s" % self.user_id) or {}
        except Exception:
            d = {}
        self._zp_base.setText("" if d.get("base_salary") is None else str(d.get("base_salary")))
        self._zp_rate.setValue(float(d.get("rate_per_hour") or 0))
        self._zp_comm.setValue(float(d.get("commission_percent") or 0))
        i = self._zp_pos.findData(d.get("position_id"))
        if i >= 0:
            self._zp_pos.setCurrentIndex(i)

    def _zp_load_acc(self):
        period = self._zp_month.currentData()
        try:
            d = self.api._e55_get("/payroll/monthly?user_id=%s&period=%s" % (self.user_id, period)) or {}
        except Exception:
            d = {}
        self._zp_adv.setValue(float(d.get("advance") or 0))
        self._zp_ded.setValue(float(d.get("deductions") or 0))
        self._zp_fin.setValue(float(d.get("fines") or 0))
        self._zp_bon.setValue(float(d.get("bonus") or 0))

    def _zp_save_me(self):
        base = self._zp_base.text().strip()
        payload = {
            "position_id": self._zp_pos.currentData(),
            "base_salary": float(base) if base else None,
            "rate_per_hour": float(self._zp_rate.value()),
            "commission_percent": float(self._zp_comm.value()),
        }
        try:
            self.api._e55_patch("/staff/payroll/%s" % self.user_id, payload)
            QMessageBox.information(self, "ЗП", "Параметры сотрудника сохранены")
        except Exception as e:
            QMessageBox.warning(self, "ЗП", str(e)[:200])

    def _zp_save_acc(self):
        period = self._zp_month.currentData()
        payload = {"period": period, "advance": float(self._zp_adv.value()),
                   "deductions": float(self._zp_ded.value()), "fines": float(self._zp_fin.value()),
                   "bonus": float(self._zp_bon.value())}
        try:
            r = self.api.session.post(self.api._url("/payroll/monthly?user_id=%s" % self.user_id),
                                      json=payload, timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "ЗП", "Начисления сохранены")
        except Exception as e:
            QMessageBox.warning(self, "ЗП", str(e)[:200])

    def _zp_load(self):
        if not hasattr(self, "_zp_tbl"):
            return
        period = self._zp_month.currentData()
        self._zp_load_acc()
        try:
            data = self.api._e55_get("/payroll/calc?period=%s" % period) or {}
            items = data.get("items", []) if isinstance(data, dict) else []
        except Exception as e:
            QMessageBox.warning(self, "Расчёт ЗП", str(e)[:200])
            items = []
        self._zp_tbl.setRowCount(0)
        for it in items:
            r = self._zp_tbl.rowCount()
            self._zp_tbl.insertRow(r)
            vals = [it.get("name"), it.get("position"), it.get("base_salary"), it.get("earnings"),
                    it.get("commission_percent"), it.get("commission"), it.get("bonus"),
                    it.get("advance"), "%s / %s" % (it.get("deductions"), it.get("fines")), it.get("total")]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(str(v if v is not None else "—"))
                if c == 9:
                    cell.setForeground(QColor("#059669"))
                self._zp_tbl.setItem(r, c, cell)

    def _render_right(self):
        while self._right_layout.count():
            it = self._right_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        created = str((self._user or {}).get("created_at") or "")[:10]
        if created:
            self._right_layout.addWidget(QLabel(f"Принят: {created}"))
        self._right_layout.addStretch(1)