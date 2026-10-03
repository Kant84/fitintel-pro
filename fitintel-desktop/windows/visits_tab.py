"""FitIntel Pro — Visits Tab (с ФИО, телефоном и кнопками впуска/выпуска)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog

from datetime import datetime, timezone

def _local(s):
    """UTC-строка от сервера -> локальное время 'YYYY-MM-DD HH:MM'."""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)[:16]

class LoadVisitsWorker(QThread):
    finished = pyqtSignal(list, dict, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            visits = self.api.get_visits()
            stats = self.api.get_visit_stats()
            clients = self.api.get_clients()
            cmap = {}
            for c in clients:
                fio = " ".join(x for x in (c.get("last_name"), c.get("first_name"),
                                           c.get("middle_name")) if x)
                cmap[str(c.get("id"))] = (fio or "—", c.get("phone") or "")
            self.finished.emit(visits, stats, cmap)
        except Exception as e:
            self.error.emit(str(e))


class VisitsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._all_data = []
        self._visible = []   # ← визиты, видимые в таблице (синхронно со строками)
        self._cmap = {}
        self._build_ui()
        QThread.msleep(0)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        cards = QHBoxLayout()
        self.lbl_today = self._stat_card("Сегодня", "0")
        self.lbl_week = self._stat_card("Неделя", "0")
        self.lbl_month = self._stat_card("Месяц", "0")
        cards.addWidget(self.lbl_today)
        cards.addWidget(self.lbl_week)
        cards.addWidget(self.lbl_month)
        cards.addStretch()

        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("Поиск по ФИО, телефону, статусу...")
        self.edit_filter.setStyleSheet(
            "QLineEdit { border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; min-width: 260px; }")
        self.edit_filter.textChanged.connect(self._filter)
        cards.addWidget(self.edit_filter)

        # === КНОПКИ ОПЕРАТОРА ===
        btn_in = QPushButton("🟢 Впустить")
        btn_in.setToolTip("Открыть вход: создать визит (ресепшен). "
                          "Команда на турникет — с v1.6")
        btn_in.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_in.clicked.connect(self._checkin)
        cards.addWidget(btn_in)

        btn_out = QPushButton("🔴 Выпустить")
        btn_out.setToolTip("Открыть выход: закрыть выбранный активный визит")
        btn_out.setStyleSheet("QPushButton { background: #ef4444; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_out.clicked.connect(self._checkout)
        cards.addWidget(btn_out)

        btn_close = QPushButton("Завершить")
        btn_close.setToolTip("Принудительно закрыть выбранный визит (без открытия турникета)")
        btn_close.setStyleSheet(self._btn_secondary())
        btn_close.clicked.connect(self._complete_selected)
        cards.addWidget(btn_close)
        # =======================

        btn = QPushButton("Обновить")
        btn.setStyleSheet(self._btn_secondary())
        btn.clicked.connect(self.refresh)
        cards.addWidget(btn)
        layout.addLayout(cards)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["№", "Клиент (ФИО)", "Телефон", "Способ входа", "Время входа", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def _stat_card(self, title: str, value: str) -> QLabel:
        lbl = QLabel(f"<b style='font-size:24px; color:{theme.fg()};'>{value}</b><br>"
                     f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")
        lbl.setStyleSheet(theme.card_style())
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _btn_secondary(self) -> str:
        return ("QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; "
                "border-radius: 6px; padding: 8px 16px; font-weight: 600; } "
                "QPushButton:hover { background: #e2e8f0; }")

    def refresh(self):
        self.worker = LoadVisitsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _card(self, lbl: QLabel, title: str, value):
        lbl.setText(f"<b style='font-size:24px; color:{theme.fg()};'>{value}</b><br>"
                    f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")

    def _on_loaded(self, visits: list, stats: dict, cmap: dict):
        self._all_data = visits
        self._cmap = cmap
        self._card(self.lbl_today, "Сегодня", stats.get("today", stats.get("today_count", 0)))
        self._card(self.lbl_week, "Неделя", stats.get("week", stats.get("week_count", 0)))
        self._card(self.lbl_month, "Месяц", stats.get("month", stats.get("month_count", 0)))
        self._render(visits)

    def _render(self, rows: list):
        self._visible = rows
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            fio, phone = self._cmap.get(str(row.get("client_id")), ("—", ""))
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(fio))
            self.table.setItem(i, 2, QTableWidgetItem(phone or "—"))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("access_method") or "—")))
            tm = _local(row.get("entry_time") or row.get("created_at")) if (row.get("entry_time") or row.get("created_at")) else "—"
            self.table.setItem(i, 4, QTableWidgetItem(tm))
            status = str(row.get("status") or "—")
            item = QTableWidgetItem(status)
            if status == "ACTIVE":
                item.setForeground(QColor("#059669"))
            elif status == "COMPLETED":
                item.setForeground(QColor("#64748b"))
            self.table.setItem(i, 5, item)
            self.table.setRowHeight(i, 28)

    def _filter(self, text: str):
        if not text:
            self._render(self._all_data)
            return
        t = text.lower()
        filtered = []
        for r in self._all_data:
            fio, phone = self._cmap.get(str(r.get("client_id")), ("", ""))
            hay = f"{fio} {phone} {r.get('status', '')} {r.get('access_method', '')}".lower()
            if t in hay:
                filtered.append(r)
        self._render(filtered)

    # ============ ВЫБРАННЫЙ ВИЗИТ ============
    def _selected_visit(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible):
            return None
        return self._visible[row]

    def _fio_of(self, visit: dict) -> str:
        return self._cmap.get(str(visit.get("client_id")), ("—", ""))[0]

    # ============ КОМАНДА НА ТУРНИКЕТ (v1.6, пока заглушка-вывоз) ============
    def _open_turnstile(self, direction: str):
        """Отправить команду открытия на терминал. Эндпоинт /skud/open появится в v1.6 —
        до тех пор просто молча пропускаем, визитная логика работает без него."""
        try:
            self.api.session.post(self.api._url("/skud/open"),
                                  json={"direction": direction, "source": "desktop"},
                                  timeout=3)
        except Exception:
            pass  # терминал недоступен / эндпоинт ещё не добавлен — не критично

    # ============ ВПУСТИТЬ (вход) ============
    def _checkin(self):
        if not self._cmap:
            QMessageBox.warning(self, "Нет данных", "Список клиентов пуст")
            return
        options = [(f"{v[0]} ({v[1]})", k) for k, v in list(self._cmap.items())[:200]]
        dlg = FormDialog("Впустить клиента (вход)", [
            ("client_id", "Клиент *", "combo", options),
            ("access_method", "Способ", "combo",
             [("Ручной (ресепшен)", "MANUAL"), ("Карта", "RFID"), ("QR", "QR"), ("Face ID", "FACE_ID")]),
            ("zone", "Зона", "text", "main"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        payload = {"client_id": v["client_id"],
                   "entry_time": datetime.now().isoformat(),
                   "access_method": v["access_method"], "zone": v["zone"] or "main"}
        try:
            r = self.api.session.post(self.api._url("/visits/manual"), json=payload)
            r.raise_for_status()
            self._open_turnstile("entry")   # открыть турникет на вход (с v1.6)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка входа", str(e))

    # ============ ВЫПУСТИТЬ (выход: закрыть визит + турникет) ============
    def _checkout(self):
        visit = self._selected_visit()
        if not visit:
            QMessageBox.warning(self, "Не выбран визит",
                                "Выделите в таблице строку с активным визитом")
            return
        if str(visit.get("status")) != "ACTIVE":
            QMessageBox.warning(self, "Визит не активен",
                                "«Выпустить» можно только для визита со статусом ACTIVE")
            return
        fio = self._fio_of(visit)
        ret = QMessageBox.question(
            self, "Выпустить клиента",
            f"Открыть выход для: <b>{fio}</b>?\nВизит будет закрыт.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        try:
            payload = {"visit_id": visit["id"],
                       "exit_time": datetime.now().isoformat()}
            r = self.api.session.post(
                self.api._url(f"/visits/{visit['id']}/complete"), json=payload)
            r.raise_for_status()
            self._open_turnstile("exit")    # открыть турникет на выход (с v1.6)
            QMessageBox.information(self, "Готово", f"{fio} выпущен, визит закрыт")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка выхода", str(e))

    # ============ ЗАВЕРШИТЬ (без турникета) ============
    def _complete_selected(self):
        visit = self._selected_visit()
        if not visit:
            QMessageBox.warning(self, "Не выбран визит",
                                "Выделите в таблице строку с визитом")
            return
        if str(visit.get("status")) != "ACTIVE":
            QMessageBox.warning(self, "Визит не активен",
                                "Этот визит уже закрыт")
            return
        fio = self._fio_of(visit)
        ret = QMessageBox.question(
            self, "Завершить визит",
            f"Принудительно закрыть визит: <b>{fio}</b>?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        try:
            payload = {"visit_id": visit["id"],
                       "exit_time": datetime.now().isoformat()}
            r = self.api.session.post(
                self.api._url(f"/visits/{visit['id']}/complete"), json=payload)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))