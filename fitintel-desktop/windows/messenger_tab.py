# -*- coding: utf-8 -*-
"""E57: «MAX сообщения» v2 — чаты, рассылки, привязки, напоминания, журнал."""
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QLineEdit,
    QSplitter, QTabWidget, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView)
from . import theme

KIND_RU = {"Акция": "promo", "Напоминание": "reminder", "Инфо": "info"}
AUD_RU = {"Клиенты": "clients", "Тренеры": "trainers", "Все": "all"}

def _t(name, *args):
    f = getattr(theme, name, None)
    if not callable(f):
        return ""
    for a in (args, ()):
        try:
            return f(*a)
        except TypeError:
            continue
        except Exception:
            return ""
    return ""

def _fio(c):
    f = c.get("fio") or c.get("full_name") or ""
    if not f:
        f = " ".join(x for x in [c.get("last_name"), c.get("first_name"),
                                 c.get("middle_name")] if x)
    return f or c.get("name") or c.get("email") or str(c.get("id"))

class Worker(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(str)
    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(str(e))

class MessengerTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._workers = []
        self._chat_id = None
        self._clients = []
        self.setStyleSheet(_t("widget_style"))
        v = QVBoxLayout(self)
        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.hide()
        v.addWidget(self.banner)

        self.sub = QTabWidget()
        v.addWidget(self.sub, 1)
        self._build_chats()
        self._build_broadcast()
        self._build_bindings()
        self._build_reminders()
        self._build_journal()
        self.load_chats()
        self.load_bindings()
        self.load_journal()
        self._run(self.api.get_clients, self._fill_clients)

    # ---------- infra ----------
    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda m: self._show(m, ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.banner.setText(str(msg))
        self.banner.setStyleSheet(_t("banner_style", ok))
        self.banner.show()

    # ---------- 1. Чаты ----------
    def _build_chats(self):
        w = QWidget()
        v = QVBoxLayout(w)
        bar = QHBoxLayout()
        for text, slot in [("Обновить", self.load_chats),
                           ("🔄 Синхронизировать MAX", self.sync_max),
                           ("＋ Демо-чат", self.demo)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        v.addLayout(bar)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.chats = QListWidget()
        self.chats.setMaximumWidth(300)
        self.chats.setStyleSheet(_t("table_style"))
        split.addWidget(self.chats)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        rv.addWidget(self.history, 1)
        sendbar = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ответ клиенту...")
        self.input.returnPressed.connect(self.send)
        b = QPushButton("Отправить")
        b.clicked.connect(self.send)
        sendbar.addWidget(self.input, 1)
        sendbar.addWidget(b)
        rv.addLayout(sendbar)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        v.addWidget(split, 1)
        self.chats.currentRowChanged.connect(self.load_messages)
        self.sub.addTab(w, "Чаты")

    def load_chats(self):
        self._run(self.api.get_chats, self._fill_chats)

    def _fill_chats(self, rows):
        rows = rows if isinstance(rows, list) else []
        self.chats.clear()
        for c in rows:
            it = QListWidgetItem("%s\n%s" % (c.get("client_name") or c.get("chat_id"),
                                             (c.get("last_message") or "")[:40]))
            it.setData(Qt.ItemDataRole.UserRole, c.get("chat_id"))
            self.chats.addItem(it)

    def load_messages(self, row):
        if row < 0:
            return
        self._chat_id = self.chats.item(row).data(Qt.ItemDataRole.UserRole)
        self._run(lambda: self.api.get_chat_messages(self._chat_id), self._fill_msgs)

    def _fill_msgs(self, rows):
        rows = rows if isinstance(rows, list) else []
        self.history.setPlainText("\n".join(
            "[%s] %s: %s" % (str(m.get("created_at") or "")[:16],
                             "Клиент" if m.get("direction") == "in" else "Вы",
                             m.get("body")) for m in rows) or "(пусто)")

    def send(self):
        text = self.input.text().strip()
        if not text or not self._chat_id:
            if not self._chat_id:
                self._show("Сначала выбери чат слева.", ok=False)
            return
        self.input.clear()
        def _done(res):
            via = " и ушёл в MAX" if isinstance(res, dict) and res.get("sent_to_max") \
                  else " (MAX не настроен — сохранён локально)"
            self._show("Отправлено" + via)
            self.load_messages(self.chats.currentRow())
            self.load_chats()
        self._run(lambda: self.api.send_chat_message(self._chat_id, text), _done)

    def sync_max(self):
        self._run(self.api.sync_max,
                  lambda r: (self._show("Синхронизация: новых %s"
                                        % (r.get("imported", 0) if isinstance(r, dict) else 0)),
                             self.load_chats()))

    def demo(self):
        self._run(self.api.demo_chat,
                  lambda _r: (self._show("Демо-чат и демо-привязка созданы."),
                              self.load_chats(), self.load_bindings()))

    # ---------- 2. Рассылка ----------
    def _build_broadcast(self):
        w = QWidget()
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("Кому:"))
        self.cmb_aud = QComboBox()
        self.cmb_aud.addItems(list(AUD_RU.keys()) + ["Конкретный клиент"])
        row.addWidget(self.cmb_aud)
        row.addWidget(QLabel("Тип:"))
        self.cmb_kind = QComboBox()
        self.cmb_kind.addItems(list(KIND_RU.keys()))
        row.addWidget(self.cmb_kind)
        row.addStretch(1)
        v.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Клиент:"))
        self.cmb_bclient = QComboBox()
        self.cmb_bclient.setEditable(True)
        self.cmb_bclient.setMinimumWidth(300)
        self.cmb_bclient.setEnabled(False)
        row2.addWidget(self.cmb_bclient, 1)
        v.addLayout(row2)
        self.cmb_aud.currentTextChanged.connect(
            lambda t: self.cmb_bclient.setEnabled(t == "Конкретный клиент"))
        self.txt_promo = QPlainTextEdit()
        self.txt_promo.setPlaceholderText(
            "Текст сообщения: акция, скидка, напоминание...")
        v.addWidget(self.txt_promo, 1)
        b = QPushButton("📣 Отправить")
        b.clicked.connect(self.do_broadcast)
        v.addWidget(b)
        note = QLabel("Рассылка уходит тем, у кого есть привязка MAX (подвкладка "
                      "«Привязки»). Статусы — в «Журнале».")
        note.setWordWrap(True)
        v.addWidget(note)
        self.sub.addTab(w, "Рассылка")

    def do_broadcast(self):
        text = self.txt_promo.toPlainText().strip()
        if not text:
            self._show("Введи текст сообщения.", ok=False)
            return
        kind = KIND_RU[self.cmb_kind.currentText()]
        aud = self.cmb_aud.currentText()
        if aud == "Конкретный клиент":
            cid = self.cmb_bclient.currentData()
            if cid is None:
                self._show("Выбери клиента.", ok=False)
                return
            self._run(lambda: self.api.notify_client(cid, text, kind),
                      lambda r: (self._show("Отправлено: sent=%s failed=%s"
                                            % (r.get("sent"), r.get("failed"))
                                            if isinstance(r, dict) else r),
                                 self.load_journal()))
        else:
            a = AUD_RU[aud]
            self._run(lambda: self.api.broadcast(a, text, kind),
                      lambda r: (self._show("Рассылка: в очереди %s, sent=%s, failed=%s"
                                            % (r.get("queued"), r.get("sent"), r.get("failed"))
                                            if isinstance(r, dict) else r),
                                 self.load_journal()))

    # ---------- 3. Привязки ----------
    def _build_bindings(self):
        w = QWidget()
        v = QVBoxLayout(w)
        note = QLabel("Бот может писать первым только тем, кто уже запустил его в "
                      "MAX. Клиент пишет боту → у него появляется user_id → "
                      "привяжи его здесь к карточке клиента.")
        note.setWordWrap(True)
        v.addWidget(note)
        bar = QHBoxLayout()
        self.cmb_bclient2 = QComboBox()
        self.cmb_bclient2.setEditable(True)
        self.cmb_bclient2.setMinimumWidth(260)
        bar.addWidget(self.cmb_bclient2, 1)
        self.ed_maxid = QLineEdit()
        self.ed_maxid.setPlaceholderText("MAX user_id")
        bar.addWidget(self.ed_maxid)
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["client", "trainer"])
        bar.addWidget(self.cmb_role)
        b = QPushButton("Привязать")
        b.clicked.connect(self.do_bind)
        bar.addWidget(b)
        v.addLayout(bar)
        self.tbl_bind = QTableWidget(0, 4)
        self.tbl_bind.setHorizontalHeaderLabels(["Клиент", "MAX user_id", "Роль", "Дата"])
        self.tbl_bind.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_bind.setStyleSheet(_t("table_style"))
        v.addWidget(self.tbl_bind, 1)
        self.sub.addTab(w, "Привязки")

    def _fill_clients(self, data):
        self._clients = data if isinstance(data, list) else []
        for cmb in (self.cmb_bclient, self.cmb_bclient2):
            cmb.clear()
            for c in self._clients:
                cmb.addItem(_fio(c), c.get("id"))

    def load_bindings(self):
        self._run(self.api.get_bindings, self._fill_bindings)

    def _fill_bindings(self, rows):
        rows = rows if isinstance(rows, list) else []
        self.tbl_bind.setRowCount(0)
        for b in rows:
            r = self.tbl_bind.rowCount()
            self.tbl_bind.insertRow(r)
            for j, val in enumerate([b.get("client_name") or b.get("client_id"),
                                     b.get("max_user_id"), b.get("role"),
                                     str(b.get("bound_at") or "")[:19]]):
                self.tbl_bind.setItem(r, j, QTableWidgetItem(str(val or "")))

    def do_bind(self):
        cid = self.cmb_bclient2.currentData()
        mid = self.ed_maxid.text().strip()
        if cid is None or not mid:
            self._show("Выбери клиента и введи MAX user_id.", ok=False)
            return
        self._run(lambda: self.api.bind_client(cid, mid,
                                               self.cmb_bclient2.currentText(),
                                               self.cmb_role.currentText()),
                  lambda _r: (self._show("Привязка сохранена."), self.load_bindings()))

    # ---------- 4. Напоминания ----------
    def _build_reminders(self):
        w = QWidget()
        v = QVBoxLayout(w)
        note = QLabel("Автоправила напоминаний:\n"
                      "• Абонемент истекает через 3 дня или меньше → напоминание о продлении\n"
                      "• Клиент не был в клубе 14+ дней → «мы скучаем»\n"
                      "Повтор в тот же день не создаётся (защита от спама). "
                      "Отправка — по привязкам MAX (см. «Журнал»).")
        note.setWordWrap(True)
        v.addWidget(note)
        b = QPushButton("🔔 Сгенерировать напоминания сейчас")
        b.clicked.connect(self.run_reminders)
        v.addWidget(b)
        v.addStretch(1)
        self.sub.addTab(w, "Напоминания")

    def run_reminders(self):
        def _done(r):
            if isinstance(r, dict):
                self._show("Создано напоминаний: %s. %s"
                           % (r.get("created"), "; ".join(r.get("notes") or [])))
            self.load_journal()
        self._run(self.api.run_reminders, _done)

    # ---------- 5. Журнал ----------
    def _build_journal(self):
        w = QWidget()
        v = QVBoxLayout(w)
        bar = QHBoxLayout()
        for text, slot in [("Обновить", self.load_journal),
                           ("📤 Отправить ожидающие", self.dispatch)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        v.addLayout(bar)
        self.tbl_j = QTableWidget(0, 5)
        self.tbl_j.setHorizontalHeaderLabels(["Создано", "Кому", "Тип", "Статус", "Текст"])
        self.tbl_j.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_j.setStyleSheet(_t("table_style"))
        v.addWidget(self.tbl_j, 1)
        self.sub.addTab(w, "Журнал")

    def load_journal(self):
        self._run(lambda: self.api.get_notifications(), self._fill_journal)

    def _fill_journal(self, rows):
        rows = rows if isinstance(rows, list) else []
        self.tbl_j.setRowCount(0)
        for n in rows:
            r = self.tbl_j.rowCount()
            self.tbl_j.insertRow(r)
            for j, val in enumerate([str(n.get("created_at") or "")[:19],
                                     n.get("target_name"), n.get("kind"),
                                     n.get("status"), (n.get("body") or "")[:80]]):
                self.tbl_j.setItem(r, j, QTableWidgetItem(str(val or "")))

    def dispatch(self):
        self._run(self.api.dispatch_notifications,
                  lambda r: (self._show("Отправка: sent=%s failed=%s"
                                        % (r.get("sent"), r.get("failed"))
                                        if isinstance(r, dict) else r),
                             self.load_journal()))
