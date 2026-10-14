from windows.form_dialog import FormDialog
"""FitIntel Pro — вкладка «Параметры клуба» (W5): временные параметры + лейблы бота.

Данные: GET/PUT /api/v1/club-params, GET/PUT /api/v1/bot-labels.
Клуб правит здесь длительность слота, окна входа, дедлайны, тексты кнопок бота.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QLabel,
    QLineEdit, QPlainTextEdit, QCheckBox, QFormLayout

    QComboBox,)
from PyQt6.QtCore import QThread, pyqtSignal

from api import ApiClient
from windows import theme


class ParamsWorker(QThread):
    finished = pyqtSignal(list)
    labels = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            r = self.api.session.get(self.api._url("/club-params"))
            r.raise_for_status()
            self.finished.emit(r.json())
            r2 = self.api.session.get(self.api._url("/bot-labels"))
            if r2.status_code == 200:
                self.labels.emit(r2.json().get("labels", {}))
        except Exception as e:
            self.error.emit(str(e))


class ClubParamsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._params = []
        self._labels = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        hint = QLabel("Все временные правила и тексты бота. Меняется сразу, без перезапуска сервера. "
                      "Двойной клик по строке — изменить значение.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tabs = QTabWidget()
        self.tbl_params = QTableWidget()
        self.tbl_params.setColumnCount(3)
        self.tbl_params.setHorizontalHeaderLabels(["Параметр", "Значение", "Описание"])
        self.tbl_params.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_params.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_params.setStyleSheet(theme.table_style())
        self.tbl_params.itemDoubleClicked.connect(self._edit_param)
        self.tabs.addTab(self.tbl_params, " Временные параметры")

        self.tbl_labels = QTableWidget()
        self.tbl_labels.setColumnCount(2)
        self.tbl_labels.setHorizontalHeaderLabels(["Лейбл", "Текст"])
        self.tbl_labels.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_labels.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_labels.setStyleSheet(theme.table_style())
        self.tbl_labels.itemDoubleClicked.connect(self._edit_label)
        self.tabs.addTab(self.tbl_labels, " Лейблы бота")
        self.tabs.addTab(BotSettingsWidget(self.api), " Настройки приложения")
        self.tabs.addTab(BonusRulesWidget(self.api), " Бонусы")
        layout.addWidget(self.tabs, 1)

        row = QHBoxLayout()
        rb = QPushButton("Обновить")
        rb.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        rb.clicked.connect(self.refresh)
        row.addWidget(rb)
        row.addStretch()
        layout.addLayout(row)

    def refresh(self):
        self.worker = ParamsWorker(self.api)
        self.worker.finished.connect(self._on_params)
        self.worker.labels.connect(self._on_labels)
        self.worker.error.connect(lambda m: QMessageBox.warning(self, "Параметры", m))
        self.worker.start()

    def _on_params(self, rows: list):
        self._params = rows
        self.tbl_params.setRowCount(len(rows))
        for i, r in enumerate(rows):
            k = QTableWidgetItem(str(r.get("key")))
            k.setData(0x0100, str(r.get("key")))   # UserRole
            self.tbl_params.setItem(i, 0, k)
            self.tbl_params.setItem(i, 1, QTableWidgetItem(str(r.get("value"))))
            self.tbl_params.setItem(i, 2, QTableWidgetItem(str(r.get("description") or "")))

    def _on_labels(self, labels: dict):
        self._labels = labels
        keys = sorted(labels.keys())
        self.tbl_labels.setRowCount(len(keys))
        for i, k in enumerate(keys):
            it = QTableWidgetItem(k)
            it.setData(0x0100, k)
            self.tbl_labels.setItem(i, 0, it)
            self.tbl_labels.setItem(i, 1, QTableWidgetItem(str(labels[k])))

    def _edit_param(self, item):
        row = item.row()
        key = self.tbl_params.item(row, 0).data(0x0100)
        cur = self.tbl_params.item(row, 1).text()
        val, ok = QInputDialog.getText(self, f"Параметр {key}", "Новое значение:", text=cur)
        if not ok or val == cur:
            return
        try:
            r = self.api.session.put(self.api._url(f"/club-params/{key}"), json={"value": val})
            if r.status_code == 200:
                QMessageBox.information(self, "Сохранено", f"{key} = {val}")
                self.refresh()
            else:
                QMessageBox.warning(self, "Не сохранено", r.text()[:200])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _edit_label(self, item):
        row = item.row()
        key = self.tbl_labels.item(row, 0).data(0x0100)
        cur = self.tbl_labels.item(row, 1).text()
        val, ok = QInputDialog.getMultiLineText(self, f"Лейбл {key}", "Текст:", text=cur)
        if not ok or val == cur:
            return
        try:
            r = self.api.session.put(self.api._url(f"/bot-labels/{key}"), json={"value": val})
            if r.status_code == 200:
                self.refresh()
            else:
                QMessageBox.warning(self, "Не сохранено", r.text()[:200])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

from PyQt6.QtWidgets import QLineEdit, QPlainTextEdit, QCheckBox, QFormLayout


# === W5: «Настройки приложения» ===
class BotCfgWorker(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(str)
    def __init__(self, fn):
        super().__init__()
        self._fn = fn
    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(str(e))


class BotSettingsWidget(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        v = QVBoxLayout(self)
        note = QLabel("Привязка бота MAX и тексты приложения. Токен — из кабинета MAX. "
                      "Адрес сервера — публичный URL системы (тест: https://fixintel.ru). "
                      "Всё сохраняется на сервере и сразу отображается в приложении и боте.")
        note.setWordWrap(True)
        v.addWidget(note)
        f = QFormLayout()
        self.ed_token = QLineEdit(); self.ed_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_token.setPlaceholderText("оставьте пустым, чтобы не менять")
        self.ed_url = QLineEdit(); self.ed_url.setPlaceholderText("https://адрес-сервера")
        self.ed_about = QPlainTextEdit(); self.ed_about.setMaximumHeight(70)
        self.ed_hours = QLineEdit()
        self.ed_phone = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_info = QLineEdit()
        self.ed_femail = QLineEdit()
        self.chk_pay = QCheckBox("Оплата услуг и товаров через приложение (баланс)")
        self.cmb_wprov = QComboBox(); self.cmb_wprov.addItems(["test", "yookassa", "sbp"])
        self.ed_wmin = QLineEdit(); self.ed_wmin.setPlaceholderText("100")
        self.ed_wbonus = QLineEdit(); self.ed_wbonus.setPlaceholderText("5")
        self.ed_ykshop = QLineEdit(); self.ed_ykshop.setPlaceholderText("shopId ЮKassa")
        self.ed_ykkey = QLineEdit(); self.ed_ykkey.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_ykkey.setPlaceholderText("секретный ключ ЮKassa")
        f.addRow("Токен бота MAX:", self.ed_token)
        f.addRow("Адрес сервера:", self.ed_url)
        f.addRow("О клубе:", self.ed_about)
        f.addRow("Часы работы:", self.ed_hours)
        f.addRow("Телефон поддержки:", self.ed_phone)
        f.addRow("Email поддержки:", self.ed_email)
        f.addRow("Email info:", self.ed_info)
        f.addRow("Email для отзывов:", self.ed_femail)
        f.addRow(self.chk_pay)
        f.addRow("Провайдер пополнения кошелька:", self.cmb_wprov)
        f.addRow("Мин. сумма пополнения, ₽:", self.ed_wmin)
        f.addRow("Бонусы от пополнения, %:", self.ed_wbonus)
        f.addRow("ЮKassa shopId:", self.ed_ykshop)
        f.addRow("ЮKassa секретный ключ:", self.ed_ykkey)
        v.addLayout(f)
        bar = QHBoxLayout()
        b1 = QPushButton(" Сохранить"); b1.clicked.connect(self.save)
        b2 = QPushButton(" Проверить"); b2.clicked.connect(self.check)
        bar.addWidget(b1); bar.addWidget(b2); bar.addStretch(1)
        v.addLayout(bar)
        self.lbl = QLabel(""); self.lbl.setWordWrap(True)
        v.addWidget(self.lbl)
        v.addStretch(1)
        self.load()

    def _run(self, fn, cb):
        w = BotCfgWorker(fn)
        w.done.connect(cb)
        w.fail.connect(lambda m: self.lbl.setText("Ошибка: " + m))
        self._worker = w  # держим ссылку: иначе GC уничтожит поток -> краш Qt
        w.start()

    def load(self):
        self._run(self.api.get_bot_config, self._fill)

    def _fill(self, r):
        if not isinstance(r, dict):
            return
        if not self.ed_url.text():
            self.ed_url.setText(r.get("api_url") or "")
        self.ed_about.setPlainText(r.get("about") or "")
        self.ed_hours.setText(r.get("hours") or "")
        self.ed_phone.setText(r.get("support_phone") or "")
        self.ed_email.setText(r.get("support_email") or "")
        self.ed_info.setText(r.get("info_email") or "")
        self.ed_femail.setText(r.get("feedback_email") or "")
        self.chk_pay.setChecked(bool(r.get("payments_enabled", True)))
        try:
            _r = self.api.session.get(self.api._url("/club-params"))
            _cp = _r.json()
            _items = _cp.get("items") if isinstance(_cp, dict) else _cp
            _pm = {}
            for _x in (_items or []):
                if isinstance(_x, dict):
                    _k = _x.get("key") or _x.get("param_key") or _x.get("name")
                    if _k:
                        _pm[str(_k)] = str(_x.get("value", ""))
            _i = self.cmb_wprov.findText(_pm.get("WALLET_PAY_PROVIDER", "test"))
            self.cmb_wprov.setCurrentIndex(max(0, _i))
            self.ed_wmin.setText(_pm.get("WALLET_TOPUP_MIN", ""))
            self.ed_wbonus.setText(_pm.get("WALLET_BONUS_PERCENT", ""))
            self.ed_ykshop.setText(_pm.get("YK_SHOP_ID", ""))
            self.ed_ykkey.setText(_pm.get("YK_SECRET_KEY", ""))
        except Exception:
            pass
        self.lbl.setText("Токен: " + ("установлен (…%s)" % r.get("bot_token_tail") if r.get("bot_token_set") else "не задан"))

    def save(self):
        body = {"api_url": self.ed_url.text().strip(), "about": self.ed_about.toPlainText().strip(),
                "hours": self.ed_hours.text().strip(), "support_phone": self.ed_phone.text().strip(),
                "support_email": self.ed_email.text().strip(),
                "info_email": self.ed_info.text().strip(),
                "feedback_email": self.ed_femail.text().strip(),
                "payments_enabled": bool(self.chk_pay.isChecked())}
        t = self.ed_token.text().strip()
        if t:
            body["bot_token"] = t
        def _done(r):
            self.ed_token.clear()
            self.lbl.setText("Сохранено. Подписка webhook обновлена автоматически.")
            self.load()

        try:
            _kv = {
                "WALLET_PAY_PROVIDER": self.cmb_wprov.currentText(),
                "WALLET_TOPUP_MIN": self.ed_wmin.text().strip(),
                "WALLET_BONUS_PERCENT": self.ed_wbonus.text().strip(),
                "YK_SHOP_ID": self.ed_ykshop.text().strip(),
                "YK_SECRET_KEY": self.ed_ykkey.text().strip(),
            }
            for _k, _v in _kv.items():
                if _v:
                    self.api.session.put(self.api._url("/club-params/" + _k), json={"value": _v})
        except Exception as _e:
            print("Кошелёк: не сохранено:", str(_e)[:150])
        self._run(lambda: self.api.save_bot_config(body), _done)

    def check(self):
        self._run(self.api.get_bot_config,
                  lambda r: self.lbl.setText("Токен: %s. Адрес: %s. Платежи: %s" % (
                      "OK (…%s)" % r.get("bot_token_tail") if r.get("bot_token_set") else "не задан",
                      r.get("api_url") or "—",
                      "вкл" if r.get("payments_enabled", True) else "выкл")))

# === W6: подвкладка «Бонусы» — правила начисления ===
CATS = {"ALL": "Все", "ADULT": "Взрослый", "CHILD": "Ребёнок", "VIP": "VIP", "STAFF": "Персонал"}
EVTS = {"topup": "Пополнение кошелька", "visit": "Посещение", "purchase": "Покупка",
        "review": "Отзыв", "subscription": "Продление абонемента"}


class BonusRulesWidget(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        v = QVBoxLayout(self)
        note = QLabel("Правила начисления бонусов: категория клиента × событие × фикс или % от суммы. "
                      "События: topup (пополнение), visit (посещение), purchase (покупка), review (отзыв), "
                      "subscription (продление). Категории: ALL, ADULT, CHILD, VIP, STAFF.")
        note.setWordWrap(True)
        v.addWidget(note)
        bar = QHBoxLayout()
        b1 = QPushButton(" Добавить"); b1.clicked.connect(self.add)
        b2 = QPushButton(" Удалить"); b2.clicked.connect(self.delete)
        b3 = QPushButton(" Обновить"); b3.clicked.connect(self.load)
        bar.addWidget(b1); bar.addWidget(b2); bar.addWidget(b3); bar.addStretch(1)
        v.addLayout(bar)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Категория", "Событие", "Тип", "Значение", "Активно"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        v.addWidget(self.table, 1)
        self.load()

    def load(self):
        try:
            data = self.api.get_bonus_rules()
            rows = data.get("items", []) if isinstance(data, dict) else []
            self.table.setRowCount(0)
            for r in rows:
                i = self.table.rowCount()
                self.table.insertRow(i)
                for j, val in enumerate([CATS.get(r.get("category"), r.get("category")),
                                         EVTS.get(r.get("event"), r.get("event")),
                                         "%" if r.get("mode") == "percent" else "фикс",
                                         str(r.get("value")),
                                         "да" if r.get("active") else "нет"]):
                    it = QTableWidgetItem(str(val))
                    if j == 0:
                        it.setData(Qt.ItemDataRole.UserRole, str(r.get("id")))
                    self.table.setItem(i, j, it)
        except Exception as e:
            QMessageBox.warning(self, "Бонусы", str(e)[:200])

    def add(self):
        dlg = FormDialog("Новое правило бонусов", [
            ("category", "Категория (Все, Взрослый, Ребёнок, VIP, Персонал)"),
            ("event", "Событие (Пополнение, Посещение, Покупка, Отзыв, Продление)"),
            ("mode", "Тип (фикс или %)"),
            ("value", "Значение (число: баллы или %)"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        raw = {k: str(val).strip() for k, val in dlg.values().items() if str(val).strip()}
        cats = {"все": "ALL", "взрослый": "ADULT", "ребёнок": "CHILD", "ребенок": "CHILD",
                "vip": "VIP", "персонал": "STAFF",
                "all": "ALL", "adult": "ADULT", "child": "CHILD", "staff": "STAFF"}
        evts = {"пополнение": "topup", "пополнение кошелька": "topup", "посещение": "visit",
                "покупка": "purchase", "отзыв": "review", "продление": "subscription",
                "продление абонемента": "subscription",
                "topup": "topup", "visit": "visit", "purchase": "purchase",
                "review": "review", "subscription": "subscription"}
        modes = {"фикс": "fix", "процент": "percent", "%": "percent",
                 "fix": "fix", "percent": "percent"}
        cat = cats.get(raw.get("category", "").lower())
        if not cat:
            QMessageBox.warning(self, "Бонусы",
                "Категория: введите «Все», «Взрослый», «Ребёнок», «VIP» или «Персонал»")
            return
        evt = evts.get(raw.get("event", "").lower())
        if not evt:
            QMessageBox.warning(self, "Бонусы",
                "Событие: введите «Пополнение», «Посещение», «Покупка», «Отзыв» или «Продление»")
            return
        mode = modes.get(raw.get("mode", "").lower())
        if not mode:
            QMessageBox.warning(self, "Бонусы",
                "Тип: введите «фикс» (баллы) или «%» (процент от суммы)")
            return
        try:
            value = float(raw.get("value", "").replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Бонусы", "Значение должно быть числом (например: 7 или 50)")
            return
        try:
            self.api.create_bonus_rule({"category": cat, "event": evt, "mode": mode, "value": value})
            self.load()
        except Exception as e:
            QMessageBox.warning(self, "Бонусы", str(e)[:200])

    def delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Бонусы", "Выберите правило в таблице")
            return
        rid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            self.api.delete_bonus_rule(rid)
            self.load()
        except Exception as e:
            QMessageBox.warning(self, "Бонусы", str(e)[:200])


from PyQt6.QtCore import Qt  # W6-fix
from PyQt6.QtWidgets import QMessageBox  # W6-fix
from windows.form_dialog import FormDialog  # W6-fix
