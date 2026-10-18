"""FitIntel Pro — Reports Tab (центр отчётов клуба)"""
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QComboBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate

from api import ApiClient
from windows import theme


REPORTS = [
    ("operational", "Операционный свод", "operational"),
    ("attendance", "Посещаемость по дням", "attendance"),
    ("hourly", "Загруженность по часам", "hourly"),
    ("inactive", "Давно не посещали (30 дн.)", "inactive"),
    ("expiring", "Окончание абонементов (14 дн.)", "expiring"),
    ("payments", "Продажи и оплаты", "payments-list"),
    ("payroll", "Зарплата тренеров", "trainer-payroll"),
    ("pnl", "P&L — прибыль/убыток (бух.)", "accounting/profit-loss"),
    ("osv", "ОСВ (бух. ведомость)", "accounting/osv"),
    ("shifts", "График работы персонала", "shifts"),
]


class ReportWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient, path: str, params: dict):
        super().__init__()
        self.api = api
        self.path = path
        self.params = params

    def run(self):
        try:
            r = self.api.session.get(self.api._url(self.path), params=self.params)
            r.raise_for_status()
            self.finished.emit(r.json())
        except Exception as e:
            self.error.emit(str(e))


class ReportsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        row.addWidget(QLabel("Отчёт:"))
        self.cmb = QComboBox()
        self.cmb.setMinimumWidth(260)
        for key, label, _path in REPORTS:
            self.cmb.addItem(label, key)
        self.cmb.currentIndexChanged.connect(lambda _i: self.refresh())
        row.addWidget(self.cmb)
        row.addWidget(QLabel("С:"))
        self.dt_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd")
        row.addWidget(self.dt_from)
        row.addWidget(QLabel("по:"))
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd")
        row.addWidget(self.dt_to)
        btn = QPushButton("Сформировать")
        btn.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        btn_csv = QPushButton(" Экспорт CSV")
        btn_csv.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_csv.clicked.connect(self.export_csv)
        row.addWidget(btn_csv)
        row.addStretch()
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        key = self.cmb.currentData()
        if not key:
            return
        path = dict((k, p) for k, _l, p in REPORTS)[key]
        params = {
            "date_from": self.dt_from.date().toString("yyyy-MM-dd"),
            "date_to": self.dt_to.date().toString("yyyy-MM-dd"),
        }
        if key == "inactive":
            params = {"days": 30}
        elif key == "expiring":
            params = {"days": 14}
        elif key in ("pnl", "osv"):
            # бухгалтерские отчёты: период = месяц из поля «по»
            params = {}
            path = path + "/" + self.dt_to.date().toString("yyyy-MM")

        url = f"/{path}" if path.startswith("accounting") else f"/reports/{path}"
        self.worker = ReportWorker(self.api, url, params)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, data: dict):
        if not isinstance(data, dict):
            self._on_error("Неожиданный ответ сервера")
            return
        if "rows" in data:
            self._fill_rows(data.get("rows") or [])
        elif "income" in data or "profit" in data:
            # P&L: плоский словарь показателей
            labels = [("income", "Доходы"), ("cost", "Себестоимость"),
                      ("expenses", "Расходы"), ("other_income", "Прочие доходы"),
                      ("profit", "Прибыль")]
            rows = [{"Показатель": label, "Сумма": data.get(k)}
                    for k, label in labels if data.get(k) is not None]
            self._fill_rows(rows)
        else:
            # Операционный свод и прочие плоские словари
            labels = {
                "revenue": "Выручка (платежи), ₽", "payments_count": "Количество платежей",
                "refunds_sum": "Возвраты, ₽", "visits_count": "Посещений (входов)",
                "new_clients": "Новых клиентов", "new_subscriptions": "Продано абонементов",
                "sales_total": "Продажи магазина, ₽",
            }
            rows = [{"Показатель": labels.get(k, k),
                     "Значение": (f"{v:,.2f}" if isinstance(v, float) else v)}
                    for k, v in data.items() if v is not None]
            self._fill_rows(rows)

    def _fill_rows(self, rows: list):
        if not rows:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["—"])
            self.table.setItem(0, 0, QTableWidgetItem(
                "Нет данных за период (или источник недоступен)"))
            return
        cols = list(rows[0].keys())
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([str(c) for c in cols])
        for i in range(len(cols)):
            self.table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.Stretch)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                val = r.get(c)
                self.table.setItem(i, j, QTableWidgetItem(
                    "" if val is None else str(val)))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["Ошибка"])
        self.table.setItem(0, 0, QTableWidgetItem(str(msg)[:200]))

    def export_csv(self):
        if self.table.columnCount() < 1 or self.table.rowCount() < 1:
            QMessageBox.information(self, "CSV", "Нет данных для выгрузки")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт отчёта",
                                              "report.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([self.table.horizontalHeaderItem(c).text()
                        if self.table.horizontalHeaderItem(c) else ""
                        for c in range(self.table.columnCount())])
            for r in range(self.table.rowCount()):
                w.writerow([self.table.item(r, c).text()
                            if self.table.item(r, c) else ""
                            for c in range(self.table.columnCount())])
        QMessageBox.information(self, "CSV", f"Сохранено: {path}")


# === E63_PRINT ===
try:
    from windows.print_helper import add_print_button as _e63_apb
    _e63_orig = ReportsTab.__init__
    def _e63_init(self, *a, **kw):
        _e63_orig(self, *a, **kw)
        try:
            _e63_apb(self, "Отчёты")
        except Exception as e:
            print("print btn:", e)
    ReportsTab.__init__ = _e63_init
    print("E63 print OK: reports_tab.py")
except Exception as e:
    print("E63 FAIL:", e)

# === EXPORT PANEL: XLSX/PDF/CSV/JSON на каждой подвкладке ===
try:
    import inspect as _inspect
    from PyQt6.QtWidgets import QWidget as _QW, QTabWidget as _QTW
    from windows.export_helper import install_export_panel as _iep

    def _install_export_panels(widget, depth=0):
        if depth > 4:
            return
        tabs = widget.findChildren(_QTW)
        if not tabs:
            _iep(widget, title=widget.__class__.__name__)
            return
        for tw in tabs:
            for i in range(tw.count()):
                page = tw.widget(i)
                if page is not None:
                    _iep(page, title=tw.tabText(i) or widget.__class__.__name__)
                    _install_export_panels(page, depth + 1)

    for _name, _obj in list(globals().items()):
        if (_inspect.isclass(_obj) and issubclass(_obj, _QW)
                and getattr(_obj, "__module__", "") == __name__
                and not _name.startswith("_")):
            _orig_init = _obj.__init__
            def _mk(orig):
                def _init(self, *a, **kw):
                    orig(self, *a, **kw)
                    try:
                        _install_export_panels(self)
                    except Exception as _e:
                        print("export panel:", _e)
                return _init
            _obj.__init__ = _mk(_orig_init)
    print("EXPORT panels OK:", __name__)
except Exception as _e:
    print("EXPORT panels FAIL:", _e)