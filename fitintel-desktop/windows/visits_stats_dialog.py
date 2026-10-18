# -*- coding: utf-8 -*-
"""Статистика посещений: сводка / VisitStats / тренд / приток-отток / по клиенту.
TODO(FastAPI): /visits/stats/trend, /clients/stats/churn-flow, /visits/stats/by-client/{id}."""
import requests as _requests
import windows.theme as theme
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton, QTabWidget, QScrollArea, QWidget, QGridLayout, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView)
from windows.icons import icon as _icon, polish as _polish
from windows.export_helper import export_table_xlsx, export_table_pdf
from app_logging import log


class VisitsStatsDialog(QDialog):
    def __init__(self, api, client_id=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.client_id = client_id  # ПОЛНЫЙ UUID или None
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Статистика посещений")
        self.resize(1000, 700)
        self._build_ui()
        self._reload()
        _polish(self)
        from windows.help_dialog import install_f1
        install_f1(self, "visits_stats")

    # ---------- UI ----------
    def _build_ui(self):
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Период:"))
        self._period = QComboBox()
        self._period.addItem("День", "day")
        self._period.addItem("Неделя", "week")
        self._period.addItem("Месяц", "month")
        self._period.addItem("Год", "year")
        self._period.setCurrentIndex(1)
        top.addWidget(self._period)
        top.addWidget(QLabel("С:"))
        self._from = QDateEdit(QDate.currentDate().addDays(-30))
        self._from.setCalendarPopup(True)
        top.addWidget(self._from)
        top.addWidget(QLabel("По:"))
        self._to = QDateEdit(QDate.currentDate())
        self._to.setCalendarPopup(True)
        top.addWidget(self._to)
        b_ref = QPushButton(" Обновить")
        b_ref.setStyleSheet("background: #10b981; color: white; border: none; "
                            "border-radius: 6px; padding: 8px 14px; font-weight: 600;")
        b_ref.clicked.connect(self._reload)
        top.addWidget(b_ref)
        top.addStretch(1)
        v.addLayout(top)

        self._tabs = QTabWidget()
        self._t_summary = self._make_tab("Сводка")
        self._t_vstats = self._make_tab("Статистика (VisitStats)")
        self._t_trend = self._make_tab("Динамика")
        self._t_churn = self._make_tab("Приток/Отток")
        if self.client_id:
            self._t_client = self._make_tab("По клиенту")
        v.addWidget(self._tabs, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        b_csv = QPushButton(" Сохранить (XLSX+PDF+CSV+JSON)")
        b_csv.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; "
                            "border: 1px solid #cbd5e1; border-radius: 6px; "
                            "padding: 6px 12px; font-weight: 600; }")
        b_csv.clicked.connect(self._save_all_formats)
        bottom.addWidget(b_csv)
        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.accept)
        bottom.addWidget(b_close)
        v.addLayout(bottom)

    def _export_csv(self):
        from PyQt6.QtWidgets import QFileDialog
        import csv as _csv
        w = self._tabs.currentWidget()
        tbl = w.findChild(QTableWidget) if w else None
        if tbl is None or tbl.rowCount() == 0:
            QMessageBox.information(self, "Экспорт", "Нет данных")
            return
        name = self._tabs.tabText(self._tabs.currentIndex())
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт CSV", f"{name}.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                wr = _csv.writer(fh, delimiter=";")
                wr.writerow([tbl.horizontalHeaderItem(i).text() for i in range(tbl.columnCount())])
                for r in range(tbl.rowCount()):
                    wr.writerow([tbl.item(r, c).text() if tbl.item(r, c) else ""
                                 for c in range(tbl.columnCount())])
            QMessageBox.information(self, "Экспорт", f"Сохранено: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Экспорт", str(e)[:200])
    def _save_all_formats(self):
        w = self._tabs.currentWidget()
        tbl = w.findChild(QTableWidget) if w else None
        if tbl is None or tbl.rowCount() == 0:
            QMessageBox.information(self, "Сохранить", "Нет данных")
            return
        from windows.export_helper import save_all_formats
        headers = [tbl.horizontalHeaderItem(i).text() for i in range(tbl.columnCount())]
        rows = [[tbl.item(r, c).text() if tbl.item(r, c) else ""
                 for c in range(tbl.columnCount())] for r in range(tbl.rowCount())]
        title = self._tabs.tabText(self._tabs.currentIndex())
        try:
            save_all_formats(self, headers, rows, title)
        except Exception as e:
            QMessageBox.warning(self, "Сохранить", str(e)[:200])
    def _make_tab(self, title):
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

    def _clear(self, w):
        lay = w._layout
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def _cards(self, lay, data_pairs):
        grid = QGridLayout()
        for i, (title, val) in enumerate(data_pairs):
            card = QFrame()
            card.setStyleSheet(theme.card_style())
            cv = QVBoxLayout(card)
            tl = QLabel(title)
            tl.setStyleSheet("color: #64748b; font-size: 11px;")
            vl = QLabel(str(val))
            f = vl.font(); f.setBold(True); f.setPointSize(16)
            vl.setFont(f)
            cv.addWidget(tl)
            cv.addWidget(vl)
            grid.addWidget(card, 0, i)
        lay.addLayout(grid)

    def _mk_table(self, lay, headers, rows):
        tbl = QTableWidget(len(rows), len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(theme.table_style())
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                tbl.setItem(r, c, QTableWidgetItem(str(val)))
        lay.addWidget(tbl)
        return tbl

    def _stub(self, lay, endpoint):
        lbl = QLabel(f"Раздел в разработке — эндпоинт {endpoint}")
        lbl.setStyleSheet("color: #64748b;")
        lay.addWidget(lbl)
        lay.addStretch(1)

    def _export_panel(self, w, tbl_getter, title):
        hb = QHBoxLayout()
        hb.addStretch()
        def _do(fmt):
            tbl = tbl_getter()
            if tbl is None or tbl.rowCount() == 0:
                QMessageBox.information(self, "Экспорт", "Нет данных")
                return
            headers = [tbl.horizontalHeaderItem(i).text() for i in range(tbl.columnCount())]
            rows = [[tbl.item(r, c).text() if tbl.item(r, c) else ""
                     for c in range(tbl.columnCount())] for r in range(tbl.rowCount())]
            try:
                if fmt == "xlsx":
                    export_table_xlsx(self, headers, rows, "visits_stats", title)
                else:
                    export_table_pdf(self, headers, rows, "visits_stats", title)
            except (RuntimeError, _requests.HTTPError) as e:
                QMessageBox.warning(self, "Экспорт", str(e)[:200])
        for fmt, label in [("xlsx", "XLSX"), ("pdf", "PDF")]:
            b = QPushButton(label)
            b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; "
                            "border: 1px solid #cbd5e1; border-radius: 6px; "
                            "padding: 6px 12px; font-weight: 600; }")
            b.clicked.connect(lambda _, f=fmt: _do(f))
            hb.addWidget(b)
        w._layout.addLayout(hb)

    # ---------- загрузка (один поток, все разделы) ----------
    def _reload(self):
        dfrom = self._from.date().toString("yyyy-MM-dd")
        dto = self._to.date().toString("yyyy-MM-dd")
        period = self._period.currentData()
        cid = self.client_id

        class _W(QThread):
            done = pyqtSignal(dict)
            def __init__(self, api):
                super().__init__(); self.api = api
            def _get(self, path, params=None):
                try:
                    r = self.api._e55_get(path, params or {})
                    return r if isinstance(r, (dict, list)) else None
                except Exception:
                    return None
            def run(self):
                res = {}
                res["summary"] = self._get("/visits/stats", {"date_from": dfrom, "date_to": dto})
                path = {"day": "/visits/stats/today",
                        "week": "/visits/stats/week",
                        "month": "/visits/stats/month"}.get(period, "/visits/stats/week")
                params = None if period == "day" else {"start_date": dfrom}
                res["vstats"] = self._get(path, params)
                res["trend"] = self._get("/visits/stats/trend",
                                         {"granularity": "week", "from": dfrom, "to": dto})
                res["churn"] = self._get("/clients/stats/churn-flow", {"period": "month"})
                if cid:
                    r = self._get(f"/visits/client/{cid}", {"limit": 200, "offset": 0})
                    res["client_visits"] = (r or {}).get("items", []) if isinstance(r, dict) else []
                self.done.emit(res)

        self._w = _W(self.api)
        self._w.done.connect(self._render_all)
        self._w.start()

    # ---------- рендер ----------
    def _render_all(self, res):
        self._render_summary(res.get("summary"))
        self._render_vstats(res.get("vstats"))
        self._render_trend(res.get("trend"))
        self._render_churn(res.get("churn"))
        if self.client_id:
            self._render_client(res.get("client_visits") or [])

    def _render_summary(self, data):
        w = self._t_summary
        self._clear(w)
        if not isinstance(data, dict):
            self._stub(w._layout, "/visits/stats")
            return
        self._cards(w._layout, [
            ("Всего", data.get("total_visits", "—")),
            ("Активны сейчас", data.get("active_visits", "—")),
            ("Завершено", data.get("completed_visits", "—")),
            ("Отказов", data.get("denied_visits", "—")),
        ])
        w._layout.addStretch(1)
        holder = {}
        def getter():
            return holder.get("t")
        w._layout.addWidget(QLabel("Период: %s — %s" % (
            (data.get("period") or {}).get("date_from", ""),
            (data.get("period") or {}).get("date_to", ""))))
        holder["t"] = self._mk_table(w._layout,
            ["Показатель", "Значение"],
            [("Сегодня", data.get("today", "—")),
             ("Неделя", data.get("week", "—")),
             ("Месяц", data.get("month", "—"))])
        self._export_panel(w, getter, "Сводка посещений")

    def _render_vstats(self, data):
        w = self._t_vstats
        self._clear(w)
        if not isinstance(data, dict):
            self._stub(w._layout, "/visits/stats/{today,week,month}")
            return
        self._cards(w._layout, [
            ("Всего", data.get("total_visits", "—")),
            ("Уникальных клиентов", data.get("unique_clients", "—")),
            ("Средняя длительность", f"{data.get('avg_duration_minutes', '—')} мин"),
        ])
        w._layout.addWidget(QLabel("По дням:"))
        by_day = data.get("visits_by_day") or []
        holder = {}
        holder["t"] = self._mk_table(w._layout, ["Дата", "Кол-во"],
            [(x.get("date", x.get("day", "")), x.get("count", x.get("visits", ""))) for x in by_day])
        zone = data.get("visits_by_zone")
        if zone:
            w._layout.addWidget(QLabel("По зонам:"))
            self._mk_table(w._layout, ["Зона", "Кол-во"],
                [(x.get("zone", ""), x.get("count", "")) for x in zone])
        w._layout.addStretch(1)
        self._export_panel(w, lambda: holder.get("t"), "Статистика посещений")

    def _render_trend(self, data):
        w = self._t_trend
        self._clear(w)
        if not isinstance(data, list):
            self._stub(w._layout, "/visits/stats/trend")
            return
        holder = {}
        holder["t"] = self._mk_table(w._layout, ["Дата", "Кол-во"],
                                     [(x.get("date", ""), x.get("count", "")) for x in data])
        w._layout.addStretch(1)
        self._export_panel(w, lambda: holder.get("t"), "Динамика посещений")

    def _render_churn(self, data):
        w = self._t_churn
        self._clear(w)
        if not isinstance(data, list):
            self._stub(w._layout, "/clients/stats/churn-flow")
            return
        rows = []
        for x in data:
            try:
                delta = int(x.get("new", 0)) - int(x.get("lost", 0))
            except Exception:
                delta = "—"
            rows.append((x.get("period", ""), x.get("new", ""), x.get("lost", ""), delta))
        holder = {}
        holder["t"] = self._mk_table(w._layout, ["Период", "Новых", "Ушло", "Δ"], rows)
        w._layout.addStretch(1)
        self._export_panel(w, lambda: holder.get("t"), "Приток/Отток клиентов")

    def _render_client(self, visits):
        w = getattr(self, "_t_client", None)
        if w is None:
            return
        self._clear(w)
        total = len(visits)
        from datetime import datetime as _dt, timedelta as _td
        cutoff = (_dt.now() - _td(days=30)).isoformat()[:10]
        month_count = sum(1 for v in visits if (v.get("entry_time") or "")[:10] >= cutoff)
        durs = [v.get("duration_minutes") for v in visits if v.get("duration_minutes")]
        avg = int(sum(durs) / len(durs)) if durs else 0
        last = max((v.get("entry_time") or "") for v in visits) if visits else "—"
        self._cards(w._layout, [
            ("Всего визитов", total),
            ("За месяц", month_count),
            ("Средняя длит.", f"{avg} мин"),
            ("Последний визит", str(last)[:16]),
        ])
        weeks = {}
        for v in visits:
            ts = (v.get("entry_time") or "")[:10]
            if not ts:
                continue
            try:
                d = _dt.fromisoformat(ts)
                y, wk, _ = d.isocalendar()
                key = f"{y}-W{wk:02d}"
                weeks[key] = weeks.get(key, 0) + 1
            except Exception:
                continue
        w._layout.addWidget(QLabel("Тренд по неделям:"))
        holder = {}
        holder["t"] = self._mk_table(w._layout, ["Неделя", "Кол-во"],
                                     sorted(weeks.items()))
        w._layout.addStretch(1)
        self._export_panel(w, lambda: holder.get("t"), "Посещения клиента")