"""E20: Бухгалтерия — ПКО/РКО, отчёты, проводки, экспорт 1С."""
import json
import urllib.request
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QComboBox, QSpinBox, QDoubleSpinBox, QFormLayout)
from PyQt6.QtCore import Qt


def _base():
    try:
        cfg = json.load(open("client_settings.json", encoding="utf-8"))
        return cfg.get("api_base") or cfg.get("base_url") or "http://localhost:8001/api/v1"
    except Exception:
        return "http://localhost:8001/api/v1"


def _token():
    try:
        cfg = json.load(open("client_settings.json", encoding="utf-8"))
        r = urllib.request.Request(_base() + "/auth/login",
            data=json.dumps({"login": cfg.get("saved_login"), "password": cfg.get("saved_password")}).encode(),
            headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(r, timeout=10)).get("access_token")
    except Exception:
        return None


def _req(method, path, data=None):
    tok = _token()
    r = urllib.request.Request(_base() + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json"}, method=method)
    if tok:
        r.add_header("Authorization", "Bearer " + tok)
    return json.load(urllib.request.urlopen(r, timeout=15))


class AccountingTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setMovable(True)
        tabs.addTab(self._cash_tab(), "💰 Касса")
        tabs.addTab(self._reports_tab(), "📊 Отчёты")
        tabs.addTab(self._entries_tab(), "📝 Проводки")
        tabs.addTab(self._export_tab(), "🔄 1С")
        lay.addWidget(tabs)

    def _cash_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Быстрые операции по кассе"))
        # ПКО
        f1 = QFormLayout()
        self.pko_amount = QDoubleSpinBox()
        self.pko_amount.setRange(0, 9999999)
        self.pko_amount.setValue(1000)
        self.pko_desc = QLineEdit("Абонемент")
        self.pko_num = QLineEdit()
        f1.addRow("Сумма:", self.pko_amount)
        f1.addRow("Описание:", self.pko_desc)
        f1.addRow("Номер:", self.pko_num)
        b1 = QPushButton("📥 ПКО (приход)")
        b1.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b1.clicked.connect(self._do_pko)
        f1.addRow(b1)
        lay.addLayout(f1)
        # РКО
        f2 = QFormLayout()
        self.rko_amount = QDoubleSpinBox()
        self.rko_amount.setRange(0, 9999999)
        self.rko_amount.setValue(500)
        self.rko_desc = QLineEdit("Расход")
        self.rko_num = QLineEdit()
        f2.addRow("Сумма:", self.rko_amount)
        f2.addRow("Описание:", self.rko_desc)
        f2.addRow("Номер:", self.rko_num)
        b2 = QPushButton("📤 РКО (расход)")
        b2.setStyleSheet("QPushButton { background: #EF4444; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b2.clicked.connect(self._do_rko)
        f2.addRow(b2)
        lay.addLayout(f2)
        self.cash_status = QLabel("")
        lay.addWidget(self.cash_status)
        lay.addStretch(1)
        return w

    def _do_pko(self):
        try:
            r = _req("POST", "/accounting/pko", {
                "amount": self.pko_amount.value(),
                "description": self.pko_desc.text(),
                "doc_number": self.pko_num.text() or None})
            self.cash_status.setText(f"✅ ПКО создан: {r.get('entry_id', '')[:8]}")
        except Exception as e:
            self.cash_status.setText("❌ " + str(e)[:150])

    def _do_rko(self):
        try:
            r = _req("POST", "/accounting/rko", {
                "amount": self.rko_amount.value(),
                "description": self.rko_desc.text(),
                "doc_number": self.rko_num.text() or None})
            self.cash_status.setText(f"✅ РКО создан: {r.get('entry_id', '')[:8]}")
        except Exception as e:
            self.cash_status.setText("❌ " + str(e)[:150])

    def _reports_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        hb = QHBoxLayout()
        self.cb_period = QComboBox()
        self.cb_period.addItems(["2026-08", "2026-07", "2026-06"])
        b_osv = QPushButton("📊 ОСВ")
        b_osv.clicked.connect(self._load_osv)
        b_pl = QPushButton("💰 Прибыль/убыток")
        b_pl.clicked.connect(self._load_pl)
        b_bs = QPushButton("⚖️ Баланс")
        b_bs.clicked.connect(self._load_bs)
        hb.addWidget(QLabel("Период:"))
        hb.addWidget(self.cb_period)
        hb.addWidget(b_osv)
        hb.addWidget(b_pl)
        hb.addWidget(b_bs)
        lay.addLayout(hb)
        self.rep_tbl = QTableWidget(0, 6)
        self.rep_tbl.setHorizontalHeaderLabels(["Счёт", "Сн Дт", "Сн Кт", "Оборот Дт", "Оборот Кт", "Ск Дт", "Ск Кт"])
        self.rep_tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.rep_tbl)
        self.rep_status = QLabel("")
        lay.addWidget(self.rep_status)
        return w

    def _load_osv(self):
        try:
            rows = _req("GET", f"/accounting/osv/{self.cb_period.currentText()}")
            self.rep_tbl.setColumnCount(7)
            self.rep_tbl.setHorizontalHeaderLabels(["Счёт", "Сн Дт", "Сн Кт", "Оборот Дт", "Оборот Кт", "Ск Дт", "Ск Кт"])
            self.rep_tbl.setRowCount(len(rows))
            for i, r in enumerate(rows):
                vals = [r.get("account"), r.get("sn_debit"), r.get("sn_credit"),
                        r.get("turnover_debit"), r.get("turnover_credit"),
                        r.get("sk_debit"), r.get("sk_credit")]
                for j, v in enumerate(vals):
                    self.rep_tbl.setItem(i, j, QTableWidgetItem(str(v if v is not None else "")))
            self.rep_status.setText(f"ОСВ: {len(rows)} счетов")
        except Exception as e:
            self.rep_status.setText("❌ " + str(e)[:150])

    def _load_pl(self):
        try:
            r = _req("GET", f"/accounting/profit-loss/{self.cb_period.currentText()}")
            self.rep_tbl.setColumnCount(2)
            self.rep_tbl.setHorizontalHeaderLabels(["Показатель", "Сумма"])
            data = [("Доходы", r.get("income")), ("Себестоимость", r.get("cost")),
                    ("Расходы", r.get("expenses")), ("Прочие доходы", r.get("other_income")),
                    ("Прибыль", r.get("profit"))]
            self.rep_tbl.setRowCount(len(data))
            for i, (k, v) in enumerate(data):
                self.rep_tbl.setItem(i, 0, QTableWidgetItem(k))
                self.rep_tbl.setItem(i, 1, QTableWidgetItem(str(v)))
            self.rep_status.setText(f"Прибыль: {r.get('profit')} руб.")
        except Exception as e:
            self.rep_status.setText("❌ " + str(e)[:150])

    def _load_bs(self):
        try:
            r = _req("GET", f"/accounting/balance-sheet/{self.cb_period.currentText()}")
            self.rep_tbl.setColumnCount(2)
            self.rep_tbl.setHorizontalHeaderLabels(["Показатель", "Сумма"])
            data = [("Активы", r.get("assets")), ("Пассивы", r.get("liabilities")),
                    ("Баланс", "OK" if r.get("balance_ok") else "ОШИБКА")]
            self.rep_tbl.setRowCount(len(data))
            for i, (k, v) in enumerate(data):
                self.rep_tbl.setItem(i, 0, QTableWidgetItem(k))
                self.rep_tbl.setItem(i, 1, QTableWidgetItem(str(v)))
            self.rep_status.setText("Баланс: " + ("сходится ✅" if r.get("balance_ok") else "не сходится ❌"))
        except Exception as e:
            self.rep_status.setText("❌ " + str(e)[:150])

    def _entries_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        b = QPushButton("🔄 Загрузить проводки")
        b.clicked.connect(self._load_entries)
        lay.addWidget(b)
        self.ent_tbl = QTableWidget(0, 6)
        self.ent_tbl.setHorizontalHeaderLabels(["ID", "Дата", "Дт", "Кт", "Сумма", "Описание"])
        self.ent_tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.ent_tbl)
        return w

    def _load_entries(self):
        try:
            r = _req("GET", "/accounting/entries?date_from=2026-08-01&date_to=2026-08-31")
            rows = r.get("entries", [])
            self.ent_tbl.setRowCount(len(rows))
            for i, e in enumerate(rows):
                for j, k in enumerate(("entry_id", "entry_date", "debit_account", "credit_account", "amount", "description")):
                    self.ent_tbl.setItem(i, j, QTableWidgetItem(str(e.get(k, ""))[:30]))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:150])

    def _export_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Экспорт в 1С (CommerceML 2.0)"))
        b1 = QPushButton("📤 Экспорт номенклатуры (mock)")
        b1.clicked.connect(lambda: QMessageBox.information(self, "1С", "Файл сгенерирован (mock-режим)"))
        lay.addWidget(b1)
        b2 = QPushButton("📤 Экспорт контрагентов (mock)")
        b2.clicked.connect(lambda: QMessageBox.information(self, "1С", "Файл сгенерирован (mock-режим)"))
        lay.addWidget(b2)
        lay.addStretch(1)
        return w
