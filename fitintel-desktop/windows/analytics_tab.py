"""W10: Аналитика — красивые графики, прогнозы, ролевые блоки. Авто-загрузка при открытии."""
import os
from datetime import date, timedelta

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QScrollArea, QFrame, QMessageBox, QFileDialog,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
)

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    _HAS_MPL = True
except Exception:
    _HAS_MPL = False

_PALETTE = ["#7C4DFF", "#00BFA5", "#FF9100", "#FF5252", "#448AFF",
            "#FFD600", "#E040FB", "#64FFDA", "#8D6E63", "#546E7A"]


def _style(fig, ax, grid_axis=None):
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fbfcfe")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#dfe3e8")
    ax.tick_params(colors="#637381", labelsize=11)
    ax.title.set_color("#212b36")
    ax.title.set_fontsize(13)
    if grid_axis:
        ax.grid(axis=grid_axis, color="#eef1f4", linewidth=0.9)
        ax.set_axisbelow(True)


def _fig(w=6, h=3):
    return Figure(figsize=(w, h), tight_layout=True)


def _lin_forecast(values, days):
    n = len(values)
    if n < 2:
        return [float(values[-1]) if values else 0.0] * days
    sx = sum(range(n)); sy = sum(values)
    den = n * sum(i * i for i in range(n)) - sx * sx
    if den == 0:
        return [float(values[-1])] * days
    a = (n * sum(i * v for i, v in enumerate(values)) - sx * sy) / den
    b = (sy - a * sx) / n
    return [a * (n + i) + b for i in range(days)]


def _fmt_int(v):
    return "{:,}".format(int(round(v))).replace(",", " ")


def _fmt_money(v):
    return _fmt_int(v) + " ₽"


class _KpiCard(QFrame):
    def __init__(self, title, color="#2E7D32", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame{background:#ffffff;border:1px solid #dfe3e8;border-radius:10px;}"
            "QLabel{background:transparent;border:none;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        self.t = QLabel(title)
        self.t.setStyleSheet("color:#637381;font-size:11px;")
        self.v = QLabel("—")
        self.v.setStyleSheet("color:%s;font-size:21px;font-weight:700;" % color)
        lay.addWidget(self.t)
        lay.addWidget(self.v)

    def set_value(self, text):
        self.v.setText(text)


class AnalyticsTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        self._data = {}
        self._ts = {}
        self._fc = {}
        self._churn = None
        self._tops = {}
        self._roles = {}
        self._canvases = []
        self._chart_row = 0

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Период:"))
        self.cb_preset = QComboBox()
        for txt, key in (("День", "day"), ("Неделя", "week"), ("Месяц", "month"),
                         ("Квартал", "quarter"), ("Год", "year"), ("Произвольно", "custom")):
            self.cb_preset.addItem(txt, key)
        self.cb_preset.setCurrentIndex(2)
        self.cb_preset.activated.connect(self._apply_preset)
        bar.addWidget(self.cb_preset)
        self.de_from = QDateEdit(QDate.currentDate().addDays(-29))
        self.de_to = QDateEdit(QDate.currentDate())
        for d in (self.de_from, self.de_to):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")
            bar.addWidget(d)
        b = QPushButton(" Обновить")
        b.clicked.connect(self._load)
        bar.addWidget(b)
        bar.addSpacing(12)
        bar.addWidget(QLabel("Прогноз:"))
        self.cb_horizon = QComboBox()
        for h in (7, 14, 30):
            self.cb_horizon.addItem("%d дн" % h, h)
        bar.addWidget(self.cb_horizon)
        self.cb_horizon.activated.connect(lambda _i: self._build_charts())
        b_png = QPushButton(" Сохранить графики (PNG)")
        b_png.clicked.connect(self._save_png)
        bar.addWidget(b_png)
        bar.addStretch(1)
        root.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll, 1)
        self.content = QWidget()
        self.vbox = QVBoxLayout(self.content)
        self.vbox.setSpacing(10)
        self.scroll.setWidget(self.content)

        self._kpi = {}
        grid = QGridLayout()
        cards = (
            ("Посещения", "#448AFF"), ("Выручка", "#00BFA5"),
            ("Приток клиентов", "#7C4DFF"), ("Отток клиентов", "#FF5252"),
            ("Абонементов продано", "#E040FB"), ("Сумма абонементов", "#8D6E63"),
            ("Средний чек", "#FF9100"), ("Визитов в день (ср.)", "#546E7A"),
            ("Прогноз выручки (+гориз.)", "#00695C"),
            ("Прогноз посещений (+гориз.)", "#0277BD"),
            ("Риск оттока (выс.+крит.)", "#C62828"),
            ("Тренд посещений", "#4527A0"),
        )
        for i, (title, color) in enumerate(cards):
            c = _KpiCard(title, color)
            self._kpi[title] = c
            grid.addWidget(c, i // 4, i % 4)
        self.vbox.addLayout(grid)

        self.charts_grid = QGridLayout()
        self.vbox.addLayout(self.charts_grid)
        self.churn_title = QLabel("")
        self.churn_title.setStyleSheet("font-weight:700;color:#212b36;")
        self.vbox.addWidget(self.churn_title)
        self.churn_table = QTableWidget(0, 4)
        self.churn_table.setHorizontalHeaderLabels(["Клиент", "Вероятность", "Риск", "Открыть"])
        self.churn_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.churn_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.churn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.churn_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.churn_table.setMinimumWidth(1100)
        self.churn_table.setMinimumHeight(260)
        self.churn_table.setMaximumHeight(210)
        self.churn_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.vbox.addWidget(self.churn_table)
        self.vbox.addStretch(1)

        self._apply_preset(2)

    def _apply_preset(self, idx):
        key = self.cb_preset.currentData()
        today = date.today()
        if key == "day":
            f_, t_ = today, today
        elif key == "week":
            f_, t_ = today - timedelta(days=6), today
        elif key == "month":
            f_, t_ = today.replace(day=1), today
        elif key == "quarter":
            q = (today.month - 1) // 3 * 3 + 1
            f_, t_ = date(today.year, q, 1), today
        elif key == "year":
            f_, t_ = date(today.year, 1, 1), today
        else:
            self._load(); return
        self.de_from.setDate(QDate(f_.year, f_.month, f_.day))
        self.de_to.setDate(QDate(t_.year, t_.month, t_.day))
        self._load()

    def _range(self):
        return (self.de_from.date().toString("yyyy-MM-dd"),
                self.de_to.date().toString("yyyy-MM-dd"))

    def _get(self, path, params=None):
        r = self.api.session.get(self.api._url(path), params=params or {}, timeout=60)
        r.raise_for_status()
        return r.json()

    def _load(self):
        if not self.api:
            return
        f_, t_ = self._range()
        horizon = self.cb_horizon.currentData()
        try:
            self._data = self._get("/analytics/full-stats", {"date_from": f_, "date_to": t_})
        except Exception as e:
            QMessageBox.warning(self, "Аналитика", "Не удалось загрузить:\n%s" % str(e)[:200])
            return
        self._ts = {}; self._fc = {}; self._churn = None; self._tops = {}; self._roles = {}
        try: self._ts = self._get("/analytics/timeseries", {"date_from": f_, "date_to": t_}).get("series", {})
        except Exception: pass
        for metric in ("revenue", "attendance"):
            try:
                self._fc[metric] = self._get("/analytics/trend-forecast",
                    {"metric": metric, "date_from": f_, "date_to": t_, "days_ahead": horizon})
            except Exception: pass
        try: self._churn = self._get("/analytics/churn-summary")
        except Exception: pass
        try: self._tops = self._get("/analytics/demand-tops", {"date_from": f_, "date_to": t_})
        except Exception: pass
        try: self._roles = self._get("/analytics/roles")
        except Exception: pass
        self._update_kpi()
        self._build_charts()
        self._update_churn()

    def _update_kpi(self):
        d = self._data
        horizon = self.cb_horizon.currentData()
        vis = sum(int(r.get("cnt") or 0) for r in d.get("visits_by_day", []))
        rev = sum(float(r.get("total") or 0) for r in d.get("revenue_by_day", []))
        pays = sum(int(r.get("cnt") or 0) for r in d.get("revenue_by_day", []))
        new_c = sum(int(r.get("cnt") or 0) for r in d.get("new_clients_by_day", []))
        lost = sum(int(r.get("cnt") or 0) for r in d.get("lost_clients_by_day", []))
        subs = sum(int(r.get("cnt") or 0) for r in d.get("subs_by_day", []))
        subs_sum = sum(float(r.get("total") or 0) for r in d.get("subs_by_day", []))
        days = max(1, len(set([r.get("d") for r in d.get("visits_by_day", [])])))
        self._kpi["Посещения"].set_value(_fmt_int(vis))
        self._kpi["Выручка"].set_value(_fmt_money(rev))
        self._kpi["Приток клиентов"].set_value(_fmt_int(new_c))
        self._kpi["Отток клиентов"].set_value(_fmt_int(lost))
        self._kpi["Абонементов продано"].set_value(_fmt_int(subs))
        self._kpi["Сумма абонементов"].set_value(_fmt_money(subs_sum))
        self._kpi["Средний чек"].set_value(_fmt_money(rev / pays) if pays else "—")
        self._kpi["Визитов в день (ср.)"].set_value(_fmt_int(vis / days))
        self._kpi["Прогноз выручки (+гориз.)"].t.setText("Прогноз выручки (+%d дн.)" % horizon)
        self._kpi["Прогноз посещений (+гориз.)"].t.setText("Прогноз посещений (+%d дн.)" % horizon)
        fc_rev = self._fc.get("revenue", {})
        fc_att = self._fc.get("attendance", {})
        self._kpi["Прогноз выручки (+гориз.)"].set_value(_fmt_money(fc_rev.get("forecast_total", 0)) if fc_rev else "—")
        self._kpi["Прогноз посещений (+гориз.)"].set_value(_fmt_int(fc_att.get("forecast_total", 0)) if fc_att else "—")
        if self._churn:
            c = self._churn.get("counts", {})
            risk = c.get("high", 0) + c.get("critical", 0)
            self._kpi["Риск оттока (выс.+крит.)"].set_value("%d из %d" % (risk, self._churn.get("total_active", 0)))
        else:
            self._kpi["Риск оттока (выс.+крит.)"].set_value("—")
        tp = self._ts.get("visits", {}).get("trend_pct")
        if tp is not None:
            arrow = "▲" if tp > 1 else ("▼" if tp < -1 else "◆")
            self._kpi["Тренд посещений"].set_value("%s %.1f%%" % (arrow, tp))
        else:
            self._kpi["Тренд посещений"].set_value("—")

    def _clear_charts(self):
        while self.charts_grid.count():
            item = self.charts_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._canvases = []
        self._chart_row = 0

    def _add_canvas(self, fig, title, row, col):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{background:#ffffff;border:1px solid #dfe3e8;border-radius:10px;}")
        lay = QVBoxLayout(frame)
        tl = QLabel(title)
        tl.setStyleSheet("font-weight:700;color:#212b36;")
        lay.addWidget(tl)
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(canvas)
        self._chart_row = getattr(self, '_chart_row', 0)
        self.charts_grid.addWidget(frame, self._chart_row, 0, 1, 2)
        self._chart_row += 1
        self._canvases.append((title, canvas))

    def _series(self, key, fallback_rows, val_key="cnt"):
        ts = self._ts.get(key)
        if ts and ts.get("dates"):
            return ts["dates"], ts["values"], ts.get("ma7")
        rows = self._data.get(fallback_rows, [])
        return ([r.get("d", "")[5:] for r in rows],
                [float(r.get(val_key) or 0) for r in rows], None)

    def _xlabels(self, ax, xs):
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([x[5:] if len(x) > 5 else x for x in xs], rotation=45, fontsize=7)

    def _overlay_forecast(self, ax, ys, fc_metric):
        horizon = self.cb_horizon.currentData()
        fc = self._fc.get(fc_metric, {})
        if fc and fc.get("forecast") and len(ys) >= 2:
            vals = [float(p.get("value") or 0) for p in fc["forecast"]]
        elif len(ys) >= 2:
            vals = _lin_forecast(ys, horizon)
        else:
            return
        ax.plot(range(len(ys) - 1, len(ys) + len(vals)), [ys[-1]] + vals,
                "--", color="#FF9100", linewidth=2, label="Прогноз")
        ax.axvline(len(ys) - 1, color="#dfe3e8", lw=1)
        ax.legend(frameon=False, fontsize=8)

    def _donut(self, title, rows, name_key, val_key, row, col):
        rows = [r for r in (rows or []) if float(r.get(val_key) or 0) > 0]
        if len(rows) > 6:
            top = sorted(rows, key=lambda r: -float(r.get(val_key) or 0))[:5]
            other = sum(float(r.get(val_key) or 0) for r in rows[5:])
            rows = top + [{name_key: "Прочие", val_key: other}]
        fig = _fig(11.5, 6.4)
        ax = fig.add_subplot(111)
        if not rows:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", color="#637381")
            ax.set_axis_off()
        else:
            vals = [float(r[val_key]) for r in rows]
            labels = [str(r.get(name_key, "—"))[:14] for r in rows]
            wedges, _ = ax.pie(vals, colors=_PALETTE[:len(vals)],
                               wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
                               startangle=90)
            total = sum(vals)
            ax.legend(wedges, ["%s — %s" % (l, _fmt_int(v)) for l, v in zip(labels, vals)],
                      loc="center left", bbox_to_anchor=(0.98, 0.5), fontsize=7, frameon=False)
            ax.text(0, 0, _fmt_int(total), ha="center", va="center",
                    fontsize=13, fontweight="bold", color="#212b36")
            ax.set_title(title + " (всего: %s)" % _fmt_int(total), fontsize=10)
        self._add_canvas(fig, title, row, col)

    def _barh(self, title, rows, name_key, val_key, row, col, money=False):
        rows = rows or []
        fig = _fig(11.5, 6.4)
        ax = fig.add_subplot(111)
        if rows:
            names = [str(r.get(name_key, "—"))[:20] for r in rows][::-1]
            vals = [float(r.get(val_key) or 0) for r in rows][::-1]
            bars = ax.barh(names, vals, color=_PALETTE[0], height=0.6)
            for b_, v in zip(bars, vals):
                ax.text(v, b_.get_y() + b_.get_height() / 2,
                        " " + (_fmt_money(v) if money else _fmt_int(v)),
                        va="center", fontsize=8, color="#212b36")
            ax.set_title(title, fontsize=10)
        else:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", color="#637381")
            ax.set_axis_off()
        _style(fig, ax, "x")
        self._add_canvas(fig, title, row, col)

    def _build_charts(self):
        self._clear_charts()
        if not _HAS_MPL:
            self.charts_grid.addWidget(QLabel("matplotlib не установлен"), 0, 0)
            return
        d = self._data
        R = self._roles
        wd_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        xs, ys, ma7 = self._series("visits", "visits_by_day")
        fig = _fig(11.5, 6.4); ax = fig.add_subplot(111)
        ax.plot(range(len(xs)), ys, marker="o", color="#448AFF", linewidth=2, label="Факт")
        if ma7 and len(ma7) == len(ys):
            ax.plot(range(len(xs)), ma7, color="#B39DDB", linewidth=1.5, label="Скользящая средняя 7")
        self._xlabels(ax, xs)
        self._overlay_forecast(ax, ys, "attendance")
        ax.set_title("Посещаемость")
        _style(fig, ax)
        self._add_canvas(fig, "Посещаемость и прогноз", 0, 0)

        xs, ys, _ = self._series("revenue", "revenue_by_day", "total")
        fig = _fig(11.5, 6.4); ax = fig.add_subplot(111)
        ax.bar(range(len(xs)), ys, color="#00BFA5", width=0.65)
        self._xlabels(ax, xs)
        ax.set_title("Выручка по дням, ₽")
        _style(fig, ax, "y")
        self._add_canvas(fig, "Выручка", 0, 1)

        xs, nys, _ = self._series("new_clients", "new_clients_by_day")
        _, lys, _ = self._series("lost_clients", "lost_clients_by_day")
        fig = _fig(11.5, 6.4); ax = fig.add_subplot(111)
        ax.plot(range(len(xs)), nys, marker="o", color="#7C4DFF", linewidth=2, label="Приток")
        ax.plot(range(min(len(xs), len(lys))), lys[:len(xs)], marker="s",
                color="#FF5252", linewidth=2, label="Отток")
        self._xlabels(ax, xs)
        self._overlay_forecast(ax, nys, "attendance")
        ax.set_title("Приток / отток клиентов")
        ax.legend(frameon=False, fontsize=8)
        _style(fig, ax)
        self._add_canvas(fig, "Приток клиентов (и отток)", 1, 0)

        fig = _fig(11.5, 6.4); ax = fig.add_subplot(111)
        rows = d.get("visits_wd_hour", [])
        hours = list(range(6, 24))
        grid = [[0.0] * len(hours) for _ in range(7)]
        for r in rows:
            wd = int(r.get("wd") or 0); hr = int(r.get("hr") or 0)
            if 0 <= wd < 7 and hr in hours:
                grid[wd][hours.index(hr)] = float(r.get("cnt") or 0)
        im = ax.imshow(grid, cmap="Purples", aspect="auto")
        ax.set_xticks(range(len(hours))); ax.set_xticklabels(hours, fontsize=8)
        ax.set_yticks(range(7)); ax.set_yticklabels(wd_names)
        ax.set_title("Тепловая карта: день недели × час")
        fig.colorbar(im, ax=ax, shrink=0.8)
        self._add_canvas(fig, "Тепловая карта посещений", 1, 1)

        self._donut("Статусы клиентов", R.get("clients_by_status"), "name", "cnt", 2, 0)
        self._donut("Выручка по типам оплат (30 дн)", R.get("revenue_by_method"), "name", "total", 2, 1)
        self._barh("Приток по источникам (30 дн)", R.get("new_by_source"), "name", "cnt", 3, 0)
        self._barh("Абонементы по тарифам (90 дн)", R.get("subs_by_tariff"), "name", "cnt", 3, 1)

        wd = R.get("visits_by_weekday") or []
        fig = _fig(11.5, 6.4); ax = fig.add_subplot(111)
        if wd:
            names = [wd_names[int(r["wd"])] for r in wd]
            vals = [int(r["cnt"]) for r in wd]
            ax.bar(names, vals, color="#448AFF", width=0.55)
            for i, v in enumerate(vals):
                ax.text(i, v, str(v), ha="center", fontsize=8, color="#212b36")
            ax.set_title("Посещения по дням недели")
        else:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", color="#637381")
            ax.set_axis_off()
        _style(fig, ax, "y")
        self._add_canvas(fig, "Загрузка по будням", 4, 0)

        self._barh("Продажи тренеров (30 дн)", R.get("trainer_sales"), "name", "total", 4, 1, money=True)

        tops = (("top_services", "Востребованность услуг", "cnt", 5, 0),
                ("top_trainers", "Загрузка тренеров", "cnt", 5, 1),
                ("top_products", "Продажи товаров", "total", 6, 0))
        for key, title, val_key, row, col in tops:
            rows = self._tops.get(key) or d.get(key, [])
            self._barh(title, rows, "name", val_key, row, col)

        xs, ys, _ = self._series("subscriptions", "subs_by_day")
        fig = _fig(11.5, 6.4); ax = fig.add_subplot(111)
        ax.bar(range(len(xs)), ys, color="#E040FB", width=0.6)
        self._xlabels(ax, xs)
        ax.set_title("Продано абонементов по дням")
        _style(fig, ax, "y")
        self._add_canvas(fig, "Продажи абонементов", 6, 1)

    def _update_churn(self):
        self.churn_table.setRowCount(0)
        if not self._churn:
            self.churn_title.setText("")
            return
        c = self._churn.get("counts", {})
        self.churn_title.setText(
            "AI-отток (модель: %s) — низкий: %d | средний: %d | высокий: %d | критический: %d"
            % (self._churn.get("model_type", "?"), c.get("low", 0), c.get("medium", 0),
               c.get("high", 0), c.get("critical", 0)))
        for row, item in enumerate(self._churn.get("top_risk", [])):
            self.churn_table.insertRow(row)
            self.churn_table.setItem(row, 0, QTableWidgetItem(str(item.get("name") or "—")))
            self.churn_table.setItem(row, 1, QTableWidgetItem(
                "%d%%" % round(float(item.get("probability") or 0) * 100)))
            lvl = item.get("risk_level", "low")
            it = QTableWidgetItem(lvl)
            it.setForeground(Qt.GlobalColor.red if lvl in ("high", "critical") else Qt.GlobalColor.darkGray)
            self.churn_table.setItem(row, 2, it)
            b = QPushButton("Карточка")
            cid = item.get("client_id")
            b.clicked.connect(lambda _c=False, _cid=cid: self._open_client(_cid))
            self.churn_table.setCellWidget(row, 3, b)

    def _open_client(self, cid):
        try:
            from windows.client_card import ClientCard
            ClientCard(self.api, cid).show()
        except Exception as e:
            QMessageBox.warning(self, "Клиент", "Не удалось открыть карточку: %s" % str(e)[:150])

    def _save_png(self):
        if not self._canvases:
            return
        out_dir = os.path.join(os.getcwd(), "export")
        os.makedirs(out_dir, exist_ok=True)
        saved = []
        for title, canvas in self._canvases:
            path = os.path.join(out_dir, "analytics_%02d.png" % (len(saved) + 1))
            try:
                canvas.figure.savefig(path, dpi=150)
                saved.append(path)
            except Exception as e:
                QMessageBox.warning(self, "Экспорт", "%s: %s" % (title, str(e)[:120]))
        if saved:
            QMessageBox.information(self, "Экспорт",
                                    "Сохранено графиков: %d\nПапка: %s" % (len(saved), out_dir))

# === W10: крупный шрифт всех таблиц вкладки ===
def _init_fonts_w10(self, *a, **k):
    _orig_init_fonts_w10(self, *a, **k)
    from PyQt6.QtWidgets import QTableWidget as _QT
    css = " QTableWidget{font-size:13px;} QHeaderView::section{font-size:12px;font-weight:600;}"
    for _t in self.findChildren(_QT):
        try:
            _t.setStyleSheet((_t.styleSheet() or "") + css)
        except Exception:
            pass

_orig_init_fonts_w10 = AnalyticsTab.__init__
AnalyticsTab.__init__ = _init_fonts_w10