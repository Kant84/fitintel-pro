"""W7: Аналитика — полная статистика клуба (KPI, графики, прогнозы)."""
import os
from datetime import date, timedelta

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QScrollArea, QFrame, QMessageBox, QFileDialog,
    QSizePolicy,
)

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    _HAS_MPL = True
except Exception:
    _HAS_MPL = False


def _lin_forecast(values, days):
    """Линейная регрессия по ряду values -> прогноз на days точек вперёд."""
    n = len(values)
    if n < 2:
        return [float(values[-1]) if values else 0.0] * days
    sx = sum(range(n))
    sy = sum(values)
    sxx = sum(i * i for i in range(n))
    sxy = sum(i * v for i, v in enumerate(values))
    denom = n * sxx - sx * sx
    if denom == 0:
        return [float(values[-1])] * days
    a = (n * sxy - sx * sy) / denom
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
            "QFrame{background:#ffffff;border:1px solid #dfe3e8;border-radius:8px;}"
            "QLabel{background:transparent;border:none;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        self.t = QLabel(title)
        self.t.setStyleSheet("color:#637381;font-size:11px;")
        self.v = QLabel("—")
        self.v.setStyleSheet("color:%s;font-size:20px;font-weight:700;" % color)
        lay.addWidget(self.t)
        lay.addWidget(self.v)

    def set_value(self, text):
        self.v.setText(text)


class AnalyticsTab(QWidget):
    """Полная статистика клуба: KPI, графики по периоду, прогнозы."""

    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        self._data = {}
        self._canvases = []

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Период:"))
        self.cb_preset = QComboBox()
        for txt, key in (("День", "day"), ("Неделя", "week"), ("Месяц", "month"),
                         ("Квартал", "quarter"), ("Год", "year"),
                         ("Произвольно", "custom")):
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
        bar.addSpacing(16)
        bar.addWidget(QLabel("Горизонт прогноза:"))
        self.cb_horizon = QComboBox()
        for h in (7, 14, 30):
            self.cb_horizon.addItem("%d дней" % h, h)
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
            ("Посещения", "#1E88E5"), ("Выручка", "#2E7D32"),
            ("Новые клиенты", "#00897B"), ("Ушедшие клиенты", "#E53935"),
            ("Абонементов продано", "#8E24AA"), ("Сумма абонементов", "#5E35B1"),
            ("Средний чек", "#FB8C00"), ("Визитов в день (ср.)", "#546E7A"),
        )
        for i, (title, color) in enumerate(cards):
            c = _KpiCard(title, color)
            self._kpi[title] = c
            grid.addWidget(c, i // 4, i % 4)
        self.vbox.addLayout(grid)

        self.charts_grid = QGridLayout()
        self.vbox.addLayout(self.charts_grid)
        self.vbox.addStretch(1)

        self._apply_preset(2)

    # ---------- периоды ----------
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
            self._load()
            return
        self.de_from.setDate(QDate(f_.year, f_.month, f_.day))
        self.de_to.setDate(QDate(t_.year, t_.month, t_.day))
        self._load()

    def _range(self):
        f_ = self.de_from.date().toString("yyyy-MM-dd")
        t_ = self.de_to.date().toString("yyyy-MM-dd")
        return f_, t_

    # ---------- данные ----------
    def _load(self):
        if not self.api:
            return
        f_, t_ = self._range()
        try:
            r = self.api.session.get(
                self.api._url("/analytics/full-stats"),
                params={"date_from": f_, "date_to": t_}, timeout=30)
            r.raise_for_status()
            self._data = r.json()
        except Exception as e:
            QMessageBox.warning(self, "Аналитика",
                                "Не удалось загрузить статистику:\n%s" % str(e)[:200])
            return
        self._update_kpi()
        self._build_charts()

    def _update_kpi(self):
        d = self._data
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
        self._kpi["Новые клиенты"].set_value(_fmt_int(new_c))
        self._kpi["Ушедшие клиенты"].set_value(_fmt_int(lost))
        self._kpi["Абонементов продано"].set_value(_fmt_int(subs))
        self._kpi["Сумма абонементов"].set_value(_fmt_money(subs_sum))
        self._kpi["Средний чек"].set_value(_fmt_money(rev / pays) if pays else "—")
        self._kpi["Визитов в день (ср.)"].set_value(_fmt_int(vis / days))

    # ---------- графики ----------
    def _clear_charts(self):
        while self.charts_grid.count():
            item = self.charts_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._canvases = []

    def _add_canvas(self, fig, title, row, col):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{background:#ffffff;border:1px solid #dfe3e8;border-radius:8px;}")
        lay = QVBoxLayout(frame)
        tl = QLabel(title)
        tl.setStyleSheet("font-weight:700;color:#212b36;")
        lay.addWidget(tl)
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(canvas)
        self.charts_grid.addWidget(frame, row, col)
        self._canvases.append((title, canvas))

    def _build_charts(self):
        self._clear_charts()
        if not _HAS_MPL:
            lbl = QLabel("matplotlib не установлен: pip install matplotlib")
            self.charts_grid.addWidget(lbl, 0, 0)
            return
        d = self._data
        horizon = self.cb_horizon.currentData()

        fig = Figure(figsize=(6, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        rows = d.get("visits_by_day", [])
        xs = [r.get("d", "")[5:] for r in rows]
        ys = [float(r.get("cnt") or 0) for r in rows]
        ax.plot(xs, ys, marker="o", color="#1E88E5", label="Факт")
        if len(ys) >= 2:
            fc = _lin_forecast(ys, horizon)
            fxs = ["+%d" % (i + 1) for i in range(horizon)]
            ax.plot(range(len(ys) - 1, len(ys) + horizon),
                    [ys[-1]] + fc, "--", color="#FB8C00", label="Прогноз")
            ax.axvline(len(ys) - 1, color="#c4cdd5", lw=1)
        ax.set_title("Посещения по дням")
        ax.legend()
        ax.grid(alpha=0.3)
        self._add_canvas(fig, "Посещаемость и прогноз", 0, 0)

        fig = Figure(figsize=(6, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        rows = d.get("revenue_by_day", [])
        xs = [r.get("d", "")[5:] for r in rows]
        ys = [float(r.get("total") or 0) for r in rows]
        ax.bar(xs, ys, color="#2E7D32")
        ax.set_title("Выручка по дням, ₽")
        ax.grid(axis="y", alpha=0.3)
        self._add_canvas(fig, "Выручка", 0, 1)

        fig = Figure(figsize=(6, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        n_rows = d.get("new_clients_by_day", [])
        l_rows = d.get("lost_clients_by_day", [])
        nxs = [r.get("d", "")[5:] for r in n_rows]
        nys = [float(r.get("cnt") or 0) for r in n_rows]
        lys = [float(r.get("cnt") or 0) for r in l_rows]
        ax.plot(nxs, nys, marker="o", color="#00897B", label="Новые")
        ax.plot(nxs[:len(lys)], lys, marker="s", color="#E53935", label="Ушедшие")
        if len(nys) >= 2:
            fc = _lin_forecast(nys, horizon)
            ax.plot(range(len(nys) - 1, len(nys) + horizon),
                    [nys[-1]] + fc, "--", color="#00897B", alpha=0.6)
            ax.axvline(len(nys) - 1, color="#c4cdd5", lw=1)
        ax.set_title("Приток / отток клиентов")
        ax.legend()
        ax.grid(alpha=0.3)
        self._add_canvas(fig, "Новые и ушедшие клиенты (+прогноз притока)", 1, 0)

        fig = Figure(figsize=(6, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        rows = d.get("visits_wd_hour", [])
        wd_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        hours = list(range(6, 24))
        grid = [[0.0] * len(hours) for _ in range(7)]
        for r in rows:
            wd = int(r.get("wd") or 0)
            hr = int(r.get("hr") or 0)
            if 0 <= wd < 7 and hr in hours:
                grid[wd][hours.index(hr)] = float(r.get("cnt") or 0)
        im = ax.imshow(grid, cmap="YlOrRd", aspect="auto")
        ax.set_xticks(range(len(hours)))
        ax.set_xticklabels(hours, fontsize=8)
        ax.set_yticks(range(7))
        ax.set_yticklabels(wd_names)
        ax.set_title("Тепловая карта: день недели × час")
        fig.colorbar(im, ax=ax, shrink=0.8)
        self._add_canvas(fig, "Тепловая карта посещений", 1, 1)

        tops = (("top_services", "Востребованность услуг", "cnt", 2, 0),
                ("top_trainers", "Загрузка тренеров", "cnt", 2, 1),
                ("top_products", "Продажи товаров", "total", 3, 0))
        for key, title, val_key, row, col in tops:
            fig = Figure(figsize=(6, 3), tight_layout=True)
            ax = fig.add_subplot(111)
            rows = d.get(key, [])
            if rows and not (len(rows) == 1 and "error" in rows[0]):
                names = [str(r.get("name") or "—")[:24] for r in rows][::-1]
                vals = [float(r.get(val_key) or 0) for r in rows][::-1]
                ax.barh(names, vals, color="#5E35B1")
                ax.set_title(title)
                ax.grid(axis="x", alpha=0.3)
            else:
                ax.text(0.5, 0.5, "Нет данных за период",
                        ha="center", va="center", color="#637381")
                ax.set_axis_off()
            self._add_canvas(fig, title, row, col)

        fig = Figure(figsize=(6, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        rows = d.get("subs_by_day", [])
        xs = [r.get("d", "")[5:] for r in rows]
        ys = [float(r.get("cnt") or 0) for r in rows]
        ax.bar(xs, ys, color="#8E24AA")
        ax.set_title("Продано абонементов по дням")
        ax.grid(axis="y", alpha=0.3)
        self._add_canvas(fig, "Продажи абонементов", 3, 1)

    def _save_png(self):
        if not self._canvases:
            return
        out_dir = os.path.join(os.getcwd(), "export")
        os.makedirs(out_dir, exist_ok=True)
        saved = []
        for title, canvas in self._canvases:
            name = "analytics_%02d.png" % (len(saved) + 1)
            path = os.path.join(out_dir, name)
            try:
                canvas.figure.savefig(path, dpi=150)
                saved.append(path)
            except Exception as e:
                QMessageBox.warning(self, "Экспорт", "%s: %s" % (title, str(e)[:120]))
        if saved:
            QMessageBox.information(
                self, "Экспорт",
                "Сохранено графиков: %d\nПапка: %s" % (len(saved), out_dir))