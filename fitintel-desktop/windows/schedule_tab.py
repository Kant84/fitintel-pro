"""FitIntel Pro — Schedule Tab (W5): три подвкладки.
«Занятия по дням» — сетка день-недели x время из Service.schedule (+ свободные места);
«Тренеры» — карточки с фото (TrainerProfile.photo_url);
«Записи» — прежняя таблица записей (добавление/отмена).
"""
import urllib.request
from datetime import date, timedelta
from uuid import UUID

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QComboBox, QDateTimeEdit, QDialogButtonBox, QTabWidget, QGridLayout,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPixmap, QFont

from api import ApiClient
from windows import theme

DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


# ---------------- данные ----------------

class ScheduleWorker(QThread):
    finished = pyqtSignal(list, list, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            r1 = self.api.session.get(self.api._url("/services"))
            r1.raise_for_status()
            services = r1.json() if isinstance(r1.json(), list) else []
            try:
                r2 = self.api.session.get(self.api._url("/trainers/profiles"))
                trainers = r2.json() if r2.status_code == 200 else []
            except Exception:
                trainers = []
            try:
                r3 = self.api.session.get(self.api._url("/users"))
                users = r3.json() if r3.status_code == 200 else []
                if isinstance(users, dict):
                    users = users.get("items", [])
            except Exception:
                users = []
            umap = {}
            for u in users or []:
                nm = u.get("full_name") or u.get("username") or u.get("name")
                if nm and u.get("id"):
                    umap[str(u["id"])] = str(nm)
            self.finished.emit(services, trainers if isinstance(trainers, list) else [], umap)
        except Exception as e:
            self.error.emit(str(e))


class BookingsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            resp = self.api.session.get(self.api._url("/services/trainer-schedule"))
            resp.raise_for_status()
            rows = resp.json()
            if isinstance(rows, dict):
                rows = rows.get("items", rows.get("schedule", []))
            self.finished.emit(rows if isinstance(rows, list) else [])
        except Exception as e:
            self.error.emit(str(e))


# ---------------- диалог записи (как раньше) ----------------

class NewBookingDialog(QDialog):
    def __init__(self, api: ApiClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.booking = None
        self.setWindowTitle("Новая запись")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)
        self.client = QComboBox()
        self._clients = []
        try:
            for c in api.get_clients():
                fio = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x) or "—"
                self._clients.append((c.get("id"), fio))
                self.client.addItem(fio)
        except Exception:
            pass
        layout.addRow("Клиент:", self.client)
        self.service = QComboBox()
        self._services = []
        try:
            resp = api.session.get(api._url("/services"))
            resp.raise_for_status()
            for s in resp.json():
                if s.get("is_active", True):
                    self._services.append((s.get("id"), s.get("name", "—")))
                    self.service.addItem(s.get("name", "—"))
        except Exception:
            pass
        layout.addRow("Услуга:", self.service)
        self.when = QDateTimeEdit()
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("yyyy-MM-dd HH:mm")
        from PyQt6.QtCore import QDateTime
        self.when.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        layout.addRow("Дата и время:", self.when)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Записать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _submit(self):
        if not self._clients or not self._services:
            QMessageBox.warning(self, "Запись", "Нет данных: проверьте клиентов и услуги")
            return
        client_id = self._clients[self.client.currentIndex()][0]
        service_id = self._services[self.service.currentIndex()][0]
        try:
            resp = self.api.session.post(
                self.api._url(f"/services/{service_id}/book"),
                json={"client_id": str(client_id),
                      "booking_date": self.when.dateTime().toString("yyyy-MM-ddTHH:mm:ss")})
            if resp.status_code == 201:
                self.booking = resp.json()
                self.accept()
            else:
                detail = "ошибка сервера"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                QMessageBox.warning(self, "Запись не создана", f"{resp.status_code}: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# ---------------- карточка тренера с фото ----------------

class TrainerCard(QFrame):
    def __init__(self, name: str, spec: str, photo_url: str, extra: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(theme.card_style())
        h = QHBoxLayout(self)
        self.photo = QLabel("📷")
        self.photo.setFixedSize(96, 96)
        self.photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo.setStyleSheet("QLabel { border: 1px dashed #888; border-radius: 6px; font-size: 28px; }")
        h.addWidget(self.photo)
        if photo_url:
            self._loader = _PhotoLoader(photo_url)
            self._loader.done.connect(self._set_photo)
            self._loader.start()
        v = QVBoxLayout()
        nm = QLabel(name)
        f = nm.font(); f.setPointSize(13); f.setBold(True); nm.setFont(f)
        v.addWidget(nm)
        if spec:
            v.addWidget(QLabel(spec))
        if extra:
            v.addWidget(QLabel(extra))
        v.addStretch(1)
        h.addLayout(v, 1)
        h.setContentsMargins(10, 10, 10, 10)

    def _set_photo(self, px: QPixmap):
        if not px.isNull():
            self.photo.setPixmap(px.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
            self.photo.setStyleSheet("")


class _PhotoLoader(QThread):
    done = pyqtSignal(object)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        px = QPixmap()
        try:
            with urllib.request.urlopen(self.url, timeout=8) as r:
                px.loadFromData(r.read())
        except Exception:
            pass
        self.done.emit(px)


# ---------------- основная вкладка ----------------

class ScheduleTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._services = []
        self._trainers = []
        self._umap = {}
        self._rows = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        btn_add = QPushButton(" Добавить запись")
        btn_add.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_add.clicked.connect(self._add_booking)
        btn_cancel = QPushButton("Отменить запись")
        btn_cancel.setStyleSheet("QPushButton { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_cancel.clicked.connect(self._cancel_booking)
        btn_refresh = QPushButton("Обновить")
        btn_refresh.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_refresh.clicked.connect(self.refresh)
        row.addWidget(btn_add)
        row.addWidget(btn_cancel)
        btn_crud = QPushButton("Изменить услугу")
        btn_crud.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_crud.clicked.connect(self._edit_service)
        btn_del = QPushButton("Удалить услугу")
        btn_del.setStyleSheet("QPushButton { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_del.clicked.connect(self._delete_service)
        row.addWidget(btn_crud)
        row.addWidget(btn_del)
        row.addStretch()
        row.addWidget(btn_refresh)
        layout.addLayout(row)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # --- подвкладка 1: занятия по дням ---
        w_grid = QWidget()
        v = QVBoxLayout(w_grid)
        self.grid_week = QTableWidget()
        self.grid_week.setColumnCount(8)
        self.grid_week.setHorizontalHeaderLabels(["Время"] + DAYS_RU)
        self.grid_week.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid_week.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.grid_week.setStyleSheet(theme.table_style())
        v.addWidget(self.grid_week)
        self.tabs.addTab(w_grid, " Занятия по дням")

        # --- подвкладка 2: тренеры ---
        self.trainers_scroll = QScrollArea()
        self.trainers_scroll.setWidgetResizable(True)
        self.trainers_host = QWidget()
        self.trainers_lay = QGridLayout(self.trainers_host)
        self.trainers_scroll.setWidget(self.trainers_host)
        self.tabs.addTab(self.trainers_scroll, " Тренеры")

        # --- подвкладка 3: записи ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Дата", "Время", "Клиент", "Услуга", "Тренер", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        self.tabs.addTab(self.table, " Записи")

    # ---------- загрузка ----------

    def refresh(self):
        self.worker = ScheduleWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(lambda m: QMessageBox.warning(self, "Расписание", m))
        self.worker.start()
        self.bworker = BookingsWorker(self.api)
        self.bworker.finished.connect(self._on_bookings)
        self.bworker.error.connect(lambda _m: None)
        self.bworker.start()

    def _on_loaded(self, services: list, trainers: list, umap: dict):
        self._services = services
        self._trainers = trainers
        self._umap = umap
        self._render_week_grid()
        self._render_trainers()

    def _on_bookings(self, rows: list):
        self._rows = rows
        self.table.setRowCount(max(len(rows), 1))
        if not rows:
            self.table.setItem(0, 0, QTableWidgetItem("Записей пока нет"))
            self.table.setSpan(0, 0, 1, 6)
            return
        for i, r in enumerate(rows):
            raw = str(r.get("booking_date") or "")
            self.table.setItem(i, 0, QTableWidgetItem(raw[:10] or "—"))
            self.table.setItem(i, 1, QTableWidgetItem(raw[11:16] or "—"))
            self.table.setItem(i, 2, QTableWidgetItem(str(r.get("client_name") or "—")))
            self.table.setItem(i, 3, QTableWidgetItem(str(r.get("service_name") or "—")))
            self.table.setItem(i, 4, QTableWidgetItem(str(r.get("trainer_name") or "—")))
            st = str(r.get("status") or "—")
            item = QTableWidgetItem(st)
            if st in ("BOOKED", "CONFIRMED", "PAID"):
                item.setForeground(QColor("#059669"))
            elif st in ("CANCELLED", "AUTO_CANCELLED", "NO_SHOW"):
                item.setForeground(QColor("#ef4444"))
            self.table.setItem(i, 5, item)

    # ---------- занятия по дням ----------

    def _render_week_grid(self):
        """Сетка: строки — время, колонки — дни; ячейка — занятия с местами."""
        cells = {}   # (day, time) -> list[str]
        times = set()
        for s in self._services:
            if not s.get("is_active", True):
                continue
            sched = s.get("schedule") or {}
            days = sched.get("days") or list(range(7))
            for sl in sched.get("time_slots") or []:
                t = sl.get("time", "")
                cap = sl.get("capacity", s.get("max_capacity", 1))
                if not t:
                    continue
                times.add(t)
                for d in days:
                    cells.setdefault((d, t), []).append(f"{s.get('name')} ({cap})")
        for t in sorted(times):
            pass
        self.grid_week.setRowCount(len(times))
        for i, t in enumerate(sorted(times)):
            self.grid_week.setItem(i, 0, QTableWidgetItem(t))
            for d in range(7):
                v = "\n".join(cells.get((d, t), []))
                it = QTableWidgetItem(v)
                if v:
                    it.setForeground(QColor("#065f46"))
                self.grid_week.setItem(i, d + 1, it)
        if not times:
            self.grid_week.setRowCount(1)
            self.grid_week.setItem(0, 0, QTableWidgetItem(
                "Расписание не заполнено — задайте «Расписание» в карточке услуги"))
            self.grid_week.setSpan(0, 0, 1, 8)

    # ---------- тренеры ----------

    def _render_trainers(self):
        while self.trainers_lay.count():
            it = self.trainers_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not self._trainers:
            self.trainers_lay.addWidget(QLabel("Профили тренеров не созданы — вкладка «Услуги» → «Новый тренер»"), 0, 0)
            return
        for i, p in enumerate(self._trainers):
            uid = str(p.get("user_id") or p.get("id") or "")
            name = self._umap.get(uid) or p.get("full_name") or p.get("specialization") or uid[:8]
            spec = str(p.get("specialization") or "")
            photo = str(p.get("photo_url") or "")
            rate = p.get("rate_per_hour")
            extra = f"Ставка: {rate} ₽/час" if rate else ""
            card = TrainerCard(str(name), spec, photo, extra)
            self.trainers_lay.addWidget(card, i // 2, i % 2)

    # ---------- действия ----------

    def _pick_service(self) -> dict | None:
        if not self._services:
            QMessageBox.information(self, "Услуги", "Нет услуг — нажмите «Демо-данные» или добавьте на экране «Услуги»")
            return None
        from PyQt6.QtWidgets import QInputDialog
        names = [f"{i+1}. {s.get('name')}" for i, s in enumerate(self._services)]
        item, ok = QInputDialog.getItem(self, "Выбор услуги", "Услуга:", names, 0, False)
        if not ok:
            return None
        return self._services[int(item.split(".")[0]) - 1]

    def _edit_service(self):
        svc = self._pick_service()
        if not svc:
            return
        from windows.services_tab import ServiceDialog
        dlg = ServiceDialog(self.api, self._trainers, {}, service=svc, parent=self)
        if dlg.exec() and getattr(dlg, "ok", False):
            self.refresh()

    def _delete_service(self):
        svc = self._pick_service()
        if not svc:
            return
        if QMessageBox.question(self, "Удаление услуги",
                                f"Удалить «{svc.get('name')}»?") != QMessageBox.StandardButton.Yes:
            return
        r = self.api.session.delete(self.api._url(f"/services/{svc['id']}"))
        (self.refresh() if r.status_code == 204 else
         QMessageBox.warning(self, "Удаление", f"{r.status_code}: {r.text[:150]}"))

    def _add_booking(self):
        dlg = NewBookingDialog(self.api, self)
        if dlg.exec() and dlg.booking:
            QMessageBox.information(self, "Запись", "Запись создана")
            self.refresh()

    def _cancel_booking(self):
        self.tabs.setCurrentIndex(2)   # переключить на «Записи»
        idx = self.table.currentRow()
        if idx < 0 or idx >= len(self._rows):
            QMessageBox.information(self, "Отмена записи", "Выберите строку в таблице «Записи»")
            return
        booking = self._rows[idx]
        bid = booking.get("id")
        name = booking.get("client_name", "—")
        dt = str(booking.get("booking_date") or "")[:16].replace("T", " ")
        if QMessageBox.question(self, "Отмена записи", f"Отменить запись:\n{name} — {dt}?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) != QMessageBox.StandardButton.Yes:
            return
        try:
            resp = self.api.session.post(self.api._url(f"/services/bookings/{bid}/cancel"))
            if resp.status_code in (200, 201, 204):
                QMessageBox.information(self, "Отмена записи", "Запись отменена")
                self.refresh()
            else:
                detail = "ошибка сервера"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                QMessageBox.warning(self, "Не удалось отменить", f"{resp.status_code}: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))