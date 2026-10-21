# -*- coding: utf-8 -*-
"""Подвкладка «Зарплата»: штатное расписание, параметры сотрудников, начисления, расчёт за месяц."""
import windows.theme as theme
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QDoubleSpinBox, QGroupBox, QGridLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QMessageBox,
    QAbstractItemView)
from windows.icons import icon as _icon, polish as _polish
from windows.export_helper import make_save_menu_button, _save_one
from app_logging import log


class PayrollTab(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._users = []
        self._build_ui()
        self._load_users()
        _polish(self)

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(QLabel("Месяц:"))
        self._month = QComboBox()
        now = QDate.currentDate()
        for i in range(12):
            d = now.addMonths(-i)
            self._month.addItem(d.toString("MMMM yyyy"), d.toString("yyyy-MM"))
        self._month.currentIndexChanged.connect(self._load_calc)
        top.addWidget(self._month)
        b_calc = QPushButton(" Рассчитать")
        b_calc.setStyleSheet("background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_calc.clicked.connect(self._load_calc)
        top.addWidget(b_calc)
        top.addStretch()
        lay.addLayout(top)
        sr = QHBoxLayout()
        sr.addWidget(QLabel("Поиск сотрудника:"))
        self._emp_filter = QLineEdit()
        self._emp_filter.setPlaceholderText("ФИО или логин...")
        self._emp_filter.textChanged.connect(self._on_emp_filter)
        sr.addWidget(self._emp_filter, 1)
        lay.addLayout(sr)


        gb_pos = QGroupBox("Штатное расписание (должность → оклад ₽/мес)")
        gp = QGridLayout(gb_pos)
        self._pos_tbl = QTableWidget(0, 2)
        self._pos_tbl.setHorizontalHeaderLabels(["Должность", "Оклад"])
        self._pos_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._pos_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._pos_tbl.setStyleSheet(theme.table_style())
        gp.addWidget(self._pos_tbl, 0, 0, 1, 4)
        for text, handler in [(" Добавить", self._pos_add), (" Изменить оклад", self._pos_edit), (" Удалить", self._pos_del)]:
            b = QPushButton(text)
            b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; font-weight: 600; }")
            b.clicked.connect(handler)
            gp.addWidget(b, 1, 1 if text.strip() == "Добавить" else (2 if "Изменить" in text else 3))
        lay.addWidget(gb_pos)

        gb_me = QGroupBox("Параметры сотрудника")
        fm = QFormLayout(gb_me)
        self._emp = QComboBox()
        self._emp.currentIndexChanged.connect(self._load_me)
        fm.addRow("Сотрудник:", self._emp)
        self._pos = QComboBox()
        fm.addRow("Должность:", self._pos)
        self._base = QLineEdit()
        self._base.setPlaceholderText("пусто = оклад из штатного расписания")
        fm.addRow("Оклад (переопределение), ₽:", self._base)
        self._rate = QDoubleSpinBox(); self._rate.setMaximum(1000000)
        fm.addRow("Ставка, ₽/ч:", self._rate)
        self._comm = QDoubleSpinBox(); self._comm.setMaximum(100)
        fm.addRow("Комиссия, %:", self._comm)
        b_save_me = QPushButton(" Сохранить параметры")
        b_save_me.setStyleSheet("background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_save_me.clicked.connect(self._save_me)
        fm.addRow(b_save_me)
        lay.addWidget(gb_me)

        gb_acc = QGroupBox("Начисления за месяц (выбранный сотрудник)")
        fa = QFormLayout(gb_acc)
        self._adv = QDoubleSpinBox(); self._adv.setMaximum(100000000)
        self._ded = QDoubleSpinBox(); self._ded.setMaximum(100000000)
        self._fin = QDoubleSpinBox(); self._fin.setMaximum(100000000)
        self._bon = QDoubleSpinBox(); self._bon.setMaximum(100000000)
        fa.addRow("Аванс, ₽:", self._adv)
        fa.addRow("Удержания, ₽:", self._ded)
        fa.addRow("Штрафы, ₽:", self._fin)
        fa.addRow("Премия, ₽:", self._bon)
        b_save_acc = QPushButton(" Сохранить начисления")
        b_save_acc.setStyleSheet("background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_save_acc.clicked.connect(self._save_acc)
        b_pay = QPushButton(" Выплачено")
        b_pay.setStyleSheet("QPushButton { background: #f59e0b; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_pay.clicked.connect(self._zp_pay)
        fa.addRow(b_pay)

        fa.addRow(b_save_acc)
        lay.addWidget(gb_acc)

        self._tbl = QTableWidget(0, 10)
        self._tbl.setHorizontalHeaderLabels(
            ["Сотрудник", "Должность", "Оклад", "Начисления(сдельные)", "Комиссия %",
             "Комиссия", "Премия", "Аванс", "Удерж./Штрафы", "Итого"])
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setStyleSheet(theme.table_style())
        lay.addWidget(self._tbl, 1)

        hb = QHBoxLayout()
        hb.addStretch()
        _btn = make_save_menu_button(self, self._export)
        _m = _btn.menu()
        _a1 = _m.addAction("1\u0421 (\u0417\u0430\u0440\u043f\u043b\u0430\u0442\u0430 XML)")
        _a1.triggered.connect(lambda _: self._export("zp1c"))
        _a2 = _m.addAction("1\u0421 (CommerceML)")
        _a2.triggered.connect(lambda _: self._export("1cml"))
        hb.addWidget(_btn)
        lay.addLayout(hb)

        self._load_positions()
        self._load_calc()
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ---------- сотрудники ----------
    def _load_users(self):
        class _W(QThread):
            done = pyqtSignal(list)
            def __init__(self, api):
                super().__init__(); self.api = api
            def run(self):
                try:
                    self.done.emit(self.api.get_users() or [])
                except Exception:
                    self.done.emit([])
        self._wu = _W(self.api)
        self._wu.done.connect(self._fill_users)
        self._wu.start()

    def _fill_users(self, users):
        self._users = users or []
        cur = self._emp.currentData()
        self._emp.blockSignals(True)
        self._emp.clear()
        _ft = getattr(self, "_emp_filter_text", "")
        for u in self._users:
            _nm = ((u.get("full_name") or "").strip() or u.get("username") or "")
            if _ft and _ft not in (_nm + " " + str(u.get("username") or "")).lower():
                continue

            name = (u.get("full_name") or "").strip() or u.get("username") or "—"
            self._emp.addItem(name, str(u.get("id")))
        i = self._emp.findData(cur)
        if i >= 0:
            self._emp.setCurrentIndex(i)
        self._emp.blockSignals(False)
        self._load_me()

    def _on_emp_filter(self, text):
        self._emp_filter_text = text.strip().lower()
        self._fill_users(self._users)
    def _current_user(self):
        return self._emp.currentData()

    # ---------- штатка ----------
    def _load_positions(self):
        try:
            data = self.api._e55_get("/staff/positions") or {}
            items = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        except Exception:
            items = []
        self._positions = items
        cur = self._pos.currentData()
        self._pos.blockSignals(True)
        self._pos.clear()
        self._pos.addItem("— не указана —", None)
        for p in items:
            self._pos.addItem(str(p.get("name")), p.get("id"))
        i = self._pos.findData(cur)
        if i >= 0:
            self._pos.setCurrentIndex(i)
        self._pos.blockSignals(False)
        self._pos_tbl.setRowCount(0)
        for p in items:
            r = self._pos_tbl.rowCount()
            self._pos_tbl.insertRow(r)
            it0 = QTableWidgetItem(str(p.get("name")))
            it0.setData(Qt.ItemDataRole.UserRole, str(p.get("id")))
            self._pos_tbl.setItem(r, 0, it0)
            self._pos_tbl.setItem(r, 1, QTableWidgetItem(str(p.get("base_salary"))))

    def _pos_add(self):
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
            self._load_positions()
        except Exception as e:
            QMessageBox.warning(self, "Штатка", str(e)[:200])

    def _pos_edit(self):
        row = self._pos_tbl.currentRow()
        if row < 0:
            return
        pid = self._pos_tbl.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name = self._pos_tbl.item(row, 0).text()
        sal, ok = QInputDialog.getDouble(self, "Должность", "Оклад ₽/мес для «%s»:" % name,
                                         float(self._pos_tbl.item(row, 1).text() or 0), 0, 100000000, 2)
        if not ok:
            return
        try:
            self.api._e55_patch("/staff/positions/%s" % pid, {"base_salary": sal})
            self._load_positions()
        except Exception as e:
            QMessageBox.warning(self, "Штатка", str(e)[:200])

    def _pos_del(self):
        row = self._pos_tbl.currentRow()
        if row < 0:
            return
        pid = self._pos_tbl.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Штатка", "Удалить должность?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api._e55_del("/staff/positions/%s" % pid)
            self._load_positions()
        except Exception as e:
            QMessageBox.warning(self, "Штатка", str(e)[:200])

    # ---------- параметры/начисления ----------
    def _load_me(self):
        uid = self._current_user()
        if not uid:
            return
        try:
            d = self.api._e55_get("/staff/payroll/%s" % uid) or {}
        except Exception:
            d = {}
        self._base.setText("" if d.get("base_salary") is None else str(d.get("base_salary")))
        self._rate.setValue(float(d.get("rate_per_hour") or 0))
        self._comm.setValue(float(d.get("commission_percent") or 0))
        i = self._pos.findData(d.get("position_id"))
        if i >= 0:
            self._pos.setCurrentIndex(i)
        self._load_acc()

    def _load_acc(self):
        uid = self._current_user()
        if not uid:
            return
        period = self._month.currentData()
        try:
            d = self.api._e55_get("/payroll/monthly?user_id=%s&period=%s" % (uid, period)) or {}
        except Exception:
            d = {}
        self._adv.setValue(float(d.get("advance") or 0))
        self._ded.setValue(float(d.get("deductions") or 0))
        self._fin.setValue(float(d.get("fines") or 0))
        self._bon.setValue(float(d.get("bonus") or 0))

    def _save_me(self):
        uid = self._current_user()
        if not uid:
            QMessageBox.information(self, "ЗП", "Выберите сотрудника")
            return
        base = self._base.text().strip()
        payload = {"position_id": self._pos.currentData(),
                   "base_salary": float(base) if base else None,
                   "rate_per_hour": float(self._rate.value()),
                   "commission_percent": float(self._comm.value())}
        try:
            self.api._e55_patch("/staff/payroll/%s" % uid, payload)
            QMessageBox.information(self, "ЗП", "Параметры сохранены")
        except Exception as e:
            QMessageBox.warning(self, "ЗП", str(e)[:200])

    def _save_acc(self):
        uid = self._current_user()
        if not uid:
            QMessageBox.information(self, "ЗП", "Выберите сотрудника")
            return
        payload = {"period": self._month.currentData(), "advance": float(self._adv.value()),
                   "deductions": float(self._ded.value()), "fines": float(self._fin.value()),
                   "bonus": float(self._bon.value())}
        try:
            r = self.api.session.post(self.api._url("/payroll/monthly?user_id=%s" % uid),
                                      json=payload, timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "ЗП", "Начисления сохранены")
        except Exception as e:
            QMessageBox.warning(self, "ЗП", str(e)[:200])

    # ---------- расчёт ----------
    def _zp_pay(self):
        uid = self._current_user()
        if not uid:
            QMessageBox.information(self, "ЗП", "Выберите сотрудника")
            return
        amount, ok = QInputDialog.getDouble(self, "Выплата ЗП", "Сумма выплаты, ₽:",
                                             float(self._adv.value()), 0, 100000000, 2)
        if not ok:
            return
        payload = {"period": self._month.currentData(), "amount": float(amount)}
        try:
            r = self.api.session.post(self.api._url("/payroll/monthly/pay?user_id=%s" % uid),
                                      json=payload, timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "ЗП", "Выплата зафиксирована: %s ₽ (%s)" % (amount, self._month.currentData()))
        except Exception as e:
            QMessageBox.warning(self, "ЗП", str(e)[:200])
    def _load_calc(self):
        if not hasattr(self, "_tbl"):
            return
        period = self._month.currentData()
        self._load_acc()
        try:
            data = self.api._e55_get("/payroll/calc?period=%s" % period) or {}
            items = data.get("items", []) if isinstance(data, dict) else []
        except Exception as e:
            QMessageBox.warning(self, "Расчёт ЗП", str(e)[:200])
            items = []
        self._tbl.setRowCount(0)
        for it in items:
            r = self._tbl.rowCount()
            self._tbl.insertRow(r)
            vals = [it.get("name"), it.get("position"), it.get("base_salary"), it.get("earnings"),
                    it.get("commission_percent"), it.get("commission"), it.get("bonus"),
                    it.get("advance"), "%s / %s" % (it.get("deductions"), it.get("fines")), it.get("total")]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(str(v if v is not None else "—"))
                if c == 9:
                    cell.setForeground(QColor("#059669"))
                self._tbl.setItem(r, c, cell)

    def _export(self, fmt):
        headers = [self._tbl.horizontalHeaderItem(i).text() for i in range(self._tbl.columnCount())]
        rows = [[self._tbl.item(r, c).text() if self._tbl.item(r, c) else ""
                 for c in range(self._tbl.columnCount())] for r in range(self._tbl.rowCount())]
        if fmt == "zp1c":
            self._export_zp_1c(headers, rows)
            return
        if fmt == "1c":
            from windows.export_helper import export_1c_xml
            export_1c_xml(self)
        elif fmt == "1cml":
            from windows.export_helper import export_1c_commerceml
            export_1c_commerceml(self)
        else:
            _save_one(self, fmt, headers, rows, "Расчёт ЗП %s" % self._month.currentData())
    def _export_zp_1c(self, headers, rows):
        from PyQt6.QtWidgets import QMessageBox
        from paths import APP_DIR
        from xml.sax.saxutils import escape
        import datetime as _dt
        period = self._month.currentData() or _dt.date.today().strftime("%Y-%m")
        d = APP_DIR / "export"
        d.mkdir(parents=True, exist_ok=True)
        path = d / ("zp_%s.xml" % period)

        def num(v):
            try:
                return float(str(v).replace("\u00a0", "").replace(" ", "").replace(",", "."))
            except Exception:
                return 0.0

        L = ['<?xml version="1.0" encoding="UTF-8"?>', '<Export>',
             '  <Payroll Month="%s" Club="\u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u043a\u043b\u0443\u0431" Generated="%s">'
             % (escape(period), _dt.datetime.now().isoformat(timespec="seconds"))]
        for row in rows:
            name = str(row[0] or "")
            position = str(row[1] or "")
            base = num(row[2]); earnings = num(row[3]); comm = num(row[5])
            bonus = num(row[6]); advance = num(row[7])
            try:
                dd, ff = [num(x) for x in str(row[8] or "0 / 0").split("/")]
            except Exception:
                dd, ff = 0.0, 0.0
            total = num(row[9])
            L.append('    <Employee name="%s" position="%s">' % (escape(name), escape(position)))
            if base: L.append('      <Accrual kind="\u041e\u043a\u043b\u0430\u0434" amount="%.2f"/>' % base)
            if earnings: L.append('      <Accrual kind="\u0421\u0434\u0435\u043b\u044c\u043d\u044b\u0435" amount="%.2f"/>' % earnings)
            if comm: L.append('      <Accrual kind="\u041a\u043e\u043c\u0438\u0441\u0441\u0438\u044f" amount="%.2f"/>' % comm)
            if bonus: L.append('      <Accrual kind="\u041f\u0440\u0435\u043c\u0438\u044f" amount="%.2f"/>' % bonus)
            if advance: L.append('      <Deduction kind="\u0410\u0432\u0430\u043d\u0441" amount="%.2f"/>' % advance)
            if dd: L.append('      <Deduction kind="\u0423\u0434\u0435\u0440\u0436\u0430\u043d\u0438\u044f" amount="%.2f"/>' % dd)
            if ff: L.append('      <Deduction kind="\u0428\u0442\u0440\u0430\u0444\u044b" amount="%.2f"/>' % ff)
            L.append('      <Total>%.2f</Total>' % total)
            L.append('      <Posting doc="\u041d\u0430\u0447\u0438\u0441\u043b\u0435\u043d\u0438\u0435 \u0437\u0430\u0440\u043f\u043b\u0430\u0442\u044b" dt="44" kt="70" amount="%.2f"/>' % total)
            L.append('      <Posting doc="\u0412\u044b\u043f\u043b\u0430\u0442\u0430 \u0437\u0430\u0440\u043f\u043b\u0430\u0442\u044b" dt="70" kt="50" amount="%.2f" note="\u0430\u0432\u0430\u043d\u0441 %.2f"/>' % (total, advance))
            L.append('    </Employee>')
        L.append('  </Payroll>')
        L.append('</Export>')
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(L))
        QMessageBox.information(self, "1\u0421 (\u0417\u0430\u0440\u043f\u043b\u0430\u0442\u0430 XML)",
                                "\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e: %s\n\u0421\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u043e\u0432: %d" % (path, len(rows)))
