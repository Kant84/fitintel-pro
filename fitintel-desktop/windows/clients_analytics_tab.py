"""W9: Клиентская аналитика — RFM, шкала посещений, отчёты, CSAT. Всё авто-загружается."""
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTabWidget, QMessageBox, QInputDialog, QGridLayout, QFrame, QSizePolicy,
)

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    _HAS_MPL = True
except Exception:
    _HAS_MPL = False


def _fmt_money(v):
    try:
        return "{:,}".format(int(round(float(v)))).replace(",", " ") + " ₽"
    except Exception:
        return "—"


class _Card(QFrame):
    def __init__(self, title, color="#2E7D32"):
        super().__init__()
        self.setStyleSheet(
            "QFrame{background:#fff;border:1px solid #dfe3e8;border-radius:8px;}"
            "QLabel{background:transparent;border:none;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        self.t = QLabel(title)
        self.t.setStyleSheet("color:#637381;font-size:11px;")
        self.v = QLabel("—")
        self.v.setStyleSheet("color:%s;font-size:18px;font-weight:700;" % color)
        lay.addWidget(self.t)
        lay.addWidget(self.v)

    def set(self, x):
        self.v.setText(str(x))


class ClientsAnalyticsTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.lbl = QLabel("Загрузка…")
        bar.addWidget(self.lbl)
        b = QPushButton(" Обновить всё")
        b.clicked.connect(self._load_all)
        bar.addWidget(b)
        bar.addStretch(1)
        root.addLayout(bar)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._w_rfm = QWidget(); self._build_rfm(self._w_rfm)
        self._w_att = QWidget(); self._build_attendance(self._w_att)
        self._w_rep = QWidget(); self._build_reports(self._w_rep)
        self._w_csat = QWidget(); self._build_csat(self._w_csat)
        self.tabs.addTab(self._w_rfm, " RFM")
        self.tabs.addTab(self._w_att, " Шкала посещений")
        self.tabs.addTab(self._w_rep, " Отчёты")
        self.tabs.addTab(self._w_csat, " CSAT")

        QTimer.singleShot(50, self._load_all)

    def _get(self, path, params=None):
        r = self.api.session.get(self.api._url(path), params=params or {}, timeout=90)
        r.raise_for_status()
        return r.json()

    def _load_all(self):
        if not self.api:
            return
        errs = []
        for name, fn in (("rfm", self._load_rfm), ("attendance", self._load_attendance),
                         ("reports", self._load_reports), ("csat", self._load_csat)):
            try:
                fn()
            except Exception as e:
                errs.append("%s: %s" % (name, str(e)[:100]))
        self.lbl.setText("Обновлено" if not errs else "Ошибки: " + "; ".join(errs))

    # ---------- RFM ----------
    def _build_rfm(self, w):
        lay = QVBoxLayout(w)
        self.rfm_canvas_holder = QGridLayout()
        lay.addLayout(self.rfm_canvas_holder)
        self.rfm_seg = QTableWidget(0, 3)
        self.rfm_seg.setHorizontalHeaderLabels(["Сегмент", "Клиентов", "Сумма платежей"])
        self.rfm_seg.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rfm_seg.setMaximumHeight(180)
        lay.addWidget(QLabel("Сегменты:"))
        lay.addWidget(self.rfm_seg)
        self.rfm_champ = QTableWidget(0, 7)
        self.rfm_champ.setHorizontalHeaderLabels(
            ["Клиент", "R", "F", "M", "Дней с визита", "Визитов", "Потрачено"])
        self.rfm_champ.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rfm_champ.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(QLabel("Топ-10 (лучшие R,F и M=1):"))
        lay.addWidget(self.rfm_champ)

    def _load_rfm(self):
        d = self._get("/analytics/clients-rfm")
        while self.rfm_canvas_holder.count():
            it = self.rfm_canvas_holder.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not d.get("available"):
            self.rfm_canvas_holder.addWidget(QLabel("RFM недоступен: " + str(d.get("reason", ""))), 0, 0)
            return
        dist = d.get("dist", {})
        if _HAS_MPL:
            fig = Figure(figsize=(7, 2.6), tight_layout=True)
            labels = ["1", "2", "3"]
            for i, (k, title) in enumerate((("R", "Recency (3=недавно)"),
                                            ("F", "Frequency (3=часто)"),
                                            ("M", "Monetary (1=большая сумма)"))):
                ax = fig.add_subplot(1, 3, i + 1)
                vals = [dist.get(k, {}).get(l, 0) for l in labels]
                ax.bar(labels, vals, color=["#E53935", "#FB8C00", "#2E7D32"])
                ax.set_title(title, fontsize=9)
            canvas = FigureCanvas(fig)
            canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.rfm_canvas_holder.addWidget(canvas, 0, 0)
        segs = d.get("segments", [])
        self.rfm_seg.setRowCount(len(segs))
        for r, s in enumerate(segs):
            self.rfm_seg.setItem(r, 0, QTableWidgetItem(str(s.get("segment"))))
            self.rfm_seg.setItem(r, 1, QTableWidgetItem(str(s.get("count"))))
            self.rfm_seg.setItem(r, 2, QTableWidgetItem(_fmt_money(s.get("monetary_sum"))))
        ch = d.get("top_champions", [])
        self.rfm_champ.setRowCount(len(ch))
        for r, c in enumerate(ch):
            self.rfm_champ.setItem(r, 0, QTableWidgetItem(str(c.get("name"))))
            for col, key in ((1, "R"), (2, "F"), (3, "M")):
                self.rfm_champ.setItem(r, col, QTableWidgetItem(str(c.get(key))))
            self.rfm_champ.setItem(r, 4, QTableWidgetItem(str(c.get("recency_days"))))
            self.rfm_champ.setItem(r, 5, QTableWidgetItem(str(c.get("frequency"))))
            self.rfm_champ.setItem(r, 6, QTableWidgetItem(_fmt_money(c.get("monetary"))))

    # ---------- attendance ----------
    def _build_attendance(self, w):
        lay = QVBoxLayout(w)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Поиск:"))
        self.att_search = QLineEdit()
        self.att_search.setPlaceholderText("ФИО…")
        self.att_search.textChanged.connect(self._att_filter)
        bar.addWidget(self.att_search, 1)
        bar.addWidget(QLabel("Топ:"))
        self.att_limit = QComboBox()
        for n in (50, 100, 200):
            self.att_limit.addItem(str(n), n)
        self.att_limit.activated.connect(lambda _i: self._load_attendance())
        bar.addWidget(self.att_limit)
        lay.addLayout(bar)
        self.att_table = QTableWidget(0, 5)
        self.att_table.setHorizontalHeaderLabels(
            ["Клиент", "Визитов всего", "За 30 дн", "Дней с визита", "В неделю (ср.)"])
        self.att_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.att_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.att_table.doubleClicked.connect(self._att_open)
        lay.addWidget(self.att_table)

    def _load_attendance(self):
        rows = self._get("/analytics/client-attendance",
                         {"limit": self.att_limit.currentData()})
        self._att_rows = rows if isinstance(rows, list) else []
        self._att_filter()

    def _att_filter(self):
        txt = self.att_search.text().lower()
        rows = [r for r in getattr(self, "_att_rows", [])
                if txt in str(r.get("name", "")).lower()]
        self.att_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.att_table.setItem(i, 0, QTableWidgetItem(str(r.get("name"))))
            self.att_table.setItem(i, 1, QTableWidgetItem(str(r.get("visits_total"))))
            self.att_table.setItem(i, 2, QTableWidgetItem(str(r.get("visits_30d"))))
            self.att_table.setItem(i, 3, QTableWidgetItem(
                str(r.get("last_visit_days") if r.get("last_visit_days") is not None else "никогда")))
            self.att_table.setItem(i, 4, QTableWidgetItem(str(r.get("avg_per_week") or "—")))

    def _att_open(self, idx):
        try:
            cid = self._att_rows[idx.row()]["client_id"]
            from windows.client_card import ClientCard
            ClientCard(self.api, cid).show()
        except Exception as e:
            QMessageBox.warning(self, "Клиент", str(e)[:150])

    # ---------- reports ----------
    def _build_reports(self, w):
        lay = QVBoxLayout(w)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Отчёт:"))
        self.rep_type = QComboBox()
        for txt, key in (("Новые клиенты", "new"), ("Рейтинг (по оплатам)", "top"),
                         ("Потерянные", "lost")):
            self.rep_type.addItem(txt, key)
        self.rep_type.activated.connect(lambda _i: self._load_reports())
        bar.addWidget(self.rep_type)
        self.rep_from = QDateEdit(QDate.currentDate().addDays(-29))
        self.rep_to = QDateEdit(QDate.currentDate())
        for d in (self.rep_from, self.rep_to):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")
            bar.addWidget(d)
        bar.addWidget(QLabel("Источник:"))
        self.rep_source = QLineEdit()
        self.rep_source.setMaximumWidth(110)
        bar.addWidget(self.rep_source)
        bar.addWidget(QLabel("Сумма от:"))
        self.rep_min = QLineEdit()
        self.rep_min.setMaximumWidth(70)
        bar.addWidget(self.rep_min)
        bar.addWidget(QLabel("Поиск:"))
        self.rep_search = QLineEdit()
        self.rep_search.setMaximumWidth(120)
        self.rep_search.textChanged.connect(lambda _t: self._rep_fill())
        bar.addWidget(self.rep_search)
        b = QPushButton(" Обновить")
        b.clicked.connect(self._load_reports)
        bar.addWidget(b)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.rep_table = QTableWidget(0, 7)
        self.rep_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rep_table.doubleClicked.connect(self._rep_open)
        lay.addWidget(self.rep_table)

    def _load_reports(self):
        t = self.rep_type.currentData()
        params = {"type": t,
                  "date_from": self.rep_from.date().toString("yyyy-MM-dd"),
                  "date_to": self.rep_to.date().toString("yyyy-MM-dd")}
        rows = self._get("/analytics/client-reports", params)
        self._rep_rows = rows if isinstance(rows, list) else []
        self._rep_fill()

    def _rep_fill(self):
        t = self.rep_type.currentData()
        txt = self.rep_search.text().lower()
        src = self.rep_source.text().lower()
        min_sum = float(self.rep_min.text()) if (self.rep_min.text() or "").isdigit() else 0
        rows = []
        for r in self._rep_rows:
            if txt and txt not in str(r.get("name", "")).lower():
                continue
            if t == "new" and src and src not in str(r.get("source", "")).lower():
                continue
            if t == "top" and min_sum and float(r.get("total") or 0) < min_sum:
                continue
            rows.append(r)
        cols = {
            "new": ["name", "phone", "created", "source", "visits_cnt", "visits_sum"],
            "top": ["name", "phone", "payments_cnt", "total", "avg_check", "last_visit"],
            "lost": ["name", "phone", "visits_cnt", "last_visit"],
        }[t]
        heads = {
            "new": ["Клиент", "Телефон", "Добавлен", "Источник", "Визитов", "Сумма"],
            "top": ["Клиент", "Телефон", "Платежей", "Сумма", "Средний чек", "Последний визит"],
            "lost": ["Клиент", "Телефон", "Визитов", "Последний визит"],
        }[t]
        self.rep_table.setColumnCount(len(cols))
        self.rep_table.setHorizontalHeaderLabels(heads)
        self.rep_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rep_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                v = r.get(c)
                if c in ("total", "avg_check", "visits_sum"):
                    v = _fmt_money(v)
                if c == "last_visit" and v:
                    v = str(v)[:10]
                self.rep_table.setItem(i, j, QTableWidgetItem("" if v is None else str(v)))

    def _rep_open(self, idx):
        try:
            cid = self._rep_rows[idx.row()]["id"]
            from windows.client_card import ClientCard
            ClientCard(self.api, cid).show()
        except Exception:
            pass

    # ---------- CSAT ----------
    def _build_csat(self, w):
        lay = QVBoxLayout(w)
        grid = QGridLayout()
        self.cs_avg = _Card("Средняя оценка", "#1E88E5")
        self.cs_pct = _Card("CSAT (доля 4-5)", "#2E7D32")
        self.cs_total = _Card("Всего отзывов", "#8E24AA")
        self.cs_pending = _Card("Ожидают опроса (мес.)", "#FB8C00")
        for i, c in enumerate((self.cs_avg, self.cs_pct, self.cs_total, self.cs_pending)):
            grid.addWidget(c, 0, i)
        lay.addLayout(grid)
        self.cs_dist = QGridLayout()
        lay.addLayout(self.cs_dist)
        self.cs_month = QTableWidget(0, 3)
        self.cs_month.setHorizontalHeaderLabels(["Месяц", "Отзывов", "Средняя"])
        self.cs_month.setMaximumHeight(150)
        lay.addWidget(QLabel("Динамика по месяцам:"))
        lay.addWidget(self.cs_month)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Без оценки в этом месяце (аудитория опроса MAX):"))
        self.cs_pending_lbl = QLabel("—")
        bar.addWidget(self.cs_pending_lbl)
        b = QPushButton(" Оценить клиента (тест)")
        b.clicked.connect(self._csat_rate)
        bar.addWidget(b)
        bar.addStretch(1)
        lay.addLayout(bar)

    def _load_csat(self):
        s = self._get("/analytics/csat/summary")
        self.cs_avg.set(round(s.get("avg", 0), 2))
        self.cs_pct.set(("%s%%" % s["csat_pct"]) if s.get("csat_pct") is not None else "—")
        self.cs_total.set(s.get("total", 0))
        p = self._get("/analytics/csat/pending")
        self.cs_pending.set(p.get("count", 0))
        self.cs_pending_lbl.setText(str(p.get("count", 0)))
        while self.cs_dist.count():
            it = self.cs_dist.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        dist = s.get("distribution", {})
        mx = max(dist.values()) if dist else 1
        for i in range(1, 6):
            cnt = int(dist.get(str(i), 0))
            lbl = QLabel("%d ★: %d" % (i, cnt))
            bar = QLabel("█" * (0 if mx == 0 else round(cnt / mx * 20)))
            bar.setStyleSheet("color:#2E7D32;")
            self.cs_dist.addWidget(lbl, i - 1, 0)
            self.cs_dist.addWidget(bar, i - 1, 1)
        m = s.get("monthly", [])
        self.cs_month.setRowCount(len(m))
        for r, row in enumerate(m):
            self.cs_month.setItem(r, 0, QTableWidgetItem(str(row.get("m"))))
            self.cs_month.setItem(r, 1, QTableWidgetItem(str(row.get("cnt"))))
            self.cs_month.setItem(r, 2, QTableWidgetItem(str(row.get("avg"))))

    def _csat_rate(self):
        cid, ok = QInputDialog.getText(self, "CSAT", "ID клиента:")
        if not ok or not cid:
            return
        score, ok2 = QInputDialog.getInt(self, "CSAT", "Оценка 1-5:", 5, 1, 5)
        if not ok2:
            return
        comment, _ok3 = QInputDialog.getText(self, "CSAT", "Комментарий (необязательно):")
        try:
            r = self.api.session.post(self.api._url("/analytics/csat"),
                                      json={"client_id": cid, "score": score,
                                            "comment": comment, "source": "desktop"},
                                      timeout=30)
            r.raise_for_status()
            QMessageBox.information(self, "CSAT", "Сохранено")
            self._load_csat()
        except Exception as e:
            QMessageBox.warning(self, "CSAT", str(e)[:150])