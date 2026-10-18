"""FitIntel Pro — Visits Tab (ФИО, телефон, кнопки впуска/выпуска, локальное время)"""
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


def _local(s):
    """UTC-строка от сервера -> локальное время 'YYYY-MM-DD HH:MM'."""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)[:16]


def _friendly_error(e) -> str:
    """Сырое исключение requests -> понятный текст для оператора (без URL и кодов)."""
    resp = getattr(e, "response", None)
    if resp is not None:
        detail = None
        try:
            data = resp.json()
            if isinstance(data, dict):
                detail = data.get("detail")
                if isinstance(detail, list):          # pydantic 422: список полей
                    parts = [f"{(d.get('loc') or [''])[-1]}: {d.get('msg')}"
                             for d in detail if isinstance(d, dict)]
                    detail = "; ".join(parts) or None
        except Exception:
            pass
        code = resp.status_code
        if code == 409:
            return detail or "Клиент уже в клубе (есть активный визит)"
        if code == 404:
            return detail or "Объект не найден на сервере"
        if code == 422:
            return f"Неверные данные: {detail or 'проверьте заполнение полей'}"
        if code == 401:
            return "Сессия истекла — выйдите из программы и войдите снова"
        if code == 403:
            return detail or "Недостаточно прав для этой операции"
        if code >= 500:
            return "Ошибка сервера. Попробуйте ещё раз; если повторится — сообщите администратору"
        return detail or f"Ошибка ({code})"
    text = str(e)
    low = text.lower()
    if any(k in low for k in ("connection", "timeout", "unreachable", "timed out")):
        return "Нет связи с сервером. Проверьте сеть/интернет и попробуйте снова"
    return text


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
        self._visible = []   # визиты, видимые в таблице (синхронно со строками)
        self._cmap = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        cards = QHBoxLayout()
        self.lbl_today = self._stat_card("Сегодня", "0")
        self.lbl_week = self._stat_card("Неделя", "0")
        self.lbl_month = self._stat_card("Месяц", "0")
        self.lbl_new_month = self._stat_card("Новых в месяц", "—")
        self.lbl_lost_month = self._stat_card("Ушедших в месяц", "—")
        cards.addWidget(self.lbl_today)
        cards.addWidget(self.lbl_week)
        cards.addWidget(self.lbl_month)
        cards.addWidget(self.lbl_new_month)
        cards.addWidget(self.lbl_lost_month)
        cards.addStretch()
        layout.addLayout(cards)

        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("Поиск по ФИО, телефону, статусу...")
        self.edit_filter.setStyleSheet(
            "QLineEdit { border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; min-width: 200px; }")
        self.edit_filter.textChanged.connect(self._filter)
        toolbar = QHBoxLayout()
        toolbar.addWidget(self.edit_filter)
        toolbar.addStretch()

        # === КНОПКИ ОПЕРАТОРА ===
        btn_in = QPushButton(" Впустить")
        btn_in.setToolTip("Открыть вход: создать визит (ресепшен). "
                          "Команда на турникет — с v1.6")
        btn_in.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_in.clicked.connect(self._checkin)
        toolbar.addWidget(btn_in)

        btn_out = QPushButton(" Выпустить")
        btn_out.setToolTip("Открыть выход: закрыть выбранный активный визит")
        btn_out.setStyleSheet("QPushButton { background: #ef4444; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_out.clicked.connect(self._checkout)
        toolbar.addWidget(btn_out)

        btn_close = QPushButton("Завершить")
        btn_close.setToolTip("Принудительно закрыть выбранный визит (без открытия турникета)")
        btn_close.setStyleSheet(self._btn_secondary())
        btn_close.clicked.connect(self._complete_selected)
        toolbar.addWidget(btn_close)
        # =======================

        btn = QPushButton("Обновить")
        btn.setStyleSheet(self._btn_secondary())
        btn.clicked.connect(self.refresh)
        toolbar.addWidget(btn)

        self.chk_staff_qr = QCheckBox(" QR сотрудников")
        self.chk_staff_qr.setToolTip("Когда включено, сотрудники проходят по входному QR без абонемента")
        self.chk_staff_qr.stateChanged.connect(self._toggle_staff_qr)
        toolbar.addWidget(self.chk_staff_qr)
        layout.addLayout(toolbar)
        self.load_staff_qr_toggle()

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

    def _toggle_staff_qr(self, state):
        val = "1" if state else "0"
        try:
            self.api.set_club_param("QR_STAFF_ENABLED", val)
            QMessageBox.information(self, "QR для сотрудников",
                                    "Служебный пропуск включён" if state else "Служебный пропуск выключен")
        except Exception as e:
            QMessageBox.warning(self, "QR для сотрудников", "Не сохранилось: %s" % _friendly_error(e))

    def load_staff_qr_toggle(self):
        try:
            data = self.api.get_club_params()
            params = {}
            if isinstance(data, dict):
                if isinstance(data.get("items"), list):
                    params = {str(p.get("key")): str(p.get("value"))
                              for p in data["items"] if isinstance(p, dict)}
                else:
                    params = {str(k): str(v) for k, v in data.items()
                              if not isinstance(v, (list, dict))}
            self.chk_staff_qr.setChecked(str(params.get("QR_STAFF_ENABLED", "0")).lower()
                                         in ("1", "true", "yes", "да"))
        except Exception:
            pass

    def refresh(self):
        self.worker = LoadVisitsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _card(self, lbl: QLabel, title: str, value):
        lbl.setText(f"<b style='font-size:24px; color:{theme.fg()};'>{value}</b><br>"
                    f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")

    @staticmethod
    def _entry_dt(row):
        try:
            return datetime.fromisoformat(str(row.get("entry_time") or row.get("created_at"))
                                          .replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    def _on_loaded(self, visits: list, stats: dict, cmap: dict):
        # Сначала активные (они всегда новее), внутри групп — по времени входа, свежие сверху
        self._all_data = sorted(
            visits,
            key=lambda r: (str(r.get("status")) != "ACTIVE", -VisitsTab._entry_dt(r).timestamp()
                           if VisitsTab._entry_dt(r) != datetime.min else 0))
        self._cmap = cmap
        self._card(self.lbl_today, "Сегодня", stats.get("today", stats.get("today_count", 0)))
        self._card(self.lbl_week, "Неделя", stats.get("week", stats.get("week_count", 0)))
        self._card(self.lbl_month, "Месяц", stats.get("month", stats.get("month_count", 0)))
        from datetime import datetime as _dtm
        _cur = _dtm.now().strftime("%Y-%m")
        def _fill_churn(data):
            for x in data:
                if str(x.get("period", "")).startswith(_cur):
                    self._card(self.lbl_new_month, "Новых в месяц", x.get("new", 0))
                    self._card(self.lbl_lost_month, "Ушедших в месяц", x.get("lost", 0))
                    return
            self._card(self.lbl_new_month, "Новых в месяц", 0)
            self._card(self.lbl_lost_month, "Ушедших в месяц", 0)
        self._churn_worker = _ChurnWorker(self.api)
        self._churn_worker.done.connect(_fill_churn)
        self._churn_worker.start()
        self._render(self._all_data)

    def _render(self, rows: list):
        self._visible = rows
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            fio, phone = self._cmap.get(str(row.get("client_id")), ("—", ""))
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(fio))
            self.table.setItem(i, 2, QTableWidgetItem(phone or "—"))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("access_method") or "—")))
            _raw = row.get("entry_time") or row.get("created_at")
            self.table.setItem(i, 4, QTableWidgetItem(_local(_raw) if _raw else "—"))
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

    # ============ КОМАНДА НА ТУРНИКЕТ (v1.6, пока заглушка) ============
    def _open_turnstile(self, direction: str):
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
            self._open_turnstile("entry")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Вход не выполнен", _friendly_error(e))
            self.refresh()   # при 409 в списке уже есть активный визит — покажем его

    # ============ ВЫПУСТИТЬ (выход) ============
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
            self._open_turnstile("exit")
            QMessageBox.information(self, "Готово", f"{fio} выпущен, визит закрыт")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Выход не выполнен", _friendly_error(e))

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
            QMessageBox.warning(self, "Не удалось завершить", _friendly_error(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        short = msg if len(msg) < 120 else msg[:117] + "..."
        self.table.setItem(0, 0, QTableWidgetItem("Не удалось загрузить данные: " + short))

# === Churn worker (module-level: стабильность PyQt, сильная ссылка self._churn_worker) ===
class _ChurnWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, api):
        super().__init__()
        self._api = api

    def run(self):
        try:
            d = self._api._e55_get("/clients/stats/churn-flow") or []
            self.done.emit(d if isinstance(d, list) else [])
        except Exception:
            self.done.emit([])