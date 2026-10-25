"""Настройки → Банки: структурный редактор BANK_CONFIG без показа секретов."""
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget,
)


COMMON_URL_HELP = (
    "Обязателен публичный адрес HTTPS, доступный банку из интернета. "
    "localhost, 192.168.x.x и адрес только внутри клуба не подходят."
)


def _field(label, help_text, example="", secret=False):
    return {
        "label": label,
        "help": help_text + (f" Пример: {example}." if example else ""),
        "secret": secret,
    }


BANKS = [
    {
        "code": "tinkoff",
        "name": "Т-Банк",
        "supported": True,
        "intro": (
            "Рабочий адаптер: создание платежа и подписанные уведомления. "
            "Данные возьмите в личном кабинете интернет-эквайринга Т-Банка. "
            "Для активации обязательны все три поля."
        ),
        "fields": {
            "terminal_key": _field(
                "Terminal Key",
                "Идентификатор терминала, а не пароль. Скопируйте Terminal Key "
                "из раздела терминалов личного кабинета. Обязательное поле; "
                "строка без пробелов в начале и конце.",
                "1234567890",
            ),
            "password": _field(
                "Пароль терминала",
                "Секретный пароль терминала. Используется и для запроса Init, "
                "и для проверки Token в webhook. Обязательное поле. Не путайте "
                "с паролем входа в личный кабинет. Значение скрыто; пустое поле "
                "при сохранении оставляет прежний секрет.",
                secret=True,
            ),
            "notification_url": _field(
                "Notification URL",
                "Адрес, на который Т-Банк отправляет результат оплаты. Укажите "
                "тот же адрес в настройках терминала. Обязательное поле. "
                + COMMON_URL_HELP,
                "https://club.example.ru/api/v1/bank/webhook",
            ),
        },
    },
    {
        "code": "sber",
        "name": "Сбербанк",
        "supported": True,
        "intro": (
            "Рабочий адаптер: register.do и проверка callback по checksum. "
            "Реквизиты выдаёт Сбер при подключении интернет-эквайринга. "
            "API-пароль и callback-ключ — разные секреты, оба обязательны."
        ),
        "fields": {
            "mode": _field(
                "Режим API",
                "Технический режим подключения. Сейчас поддерживается только "
                "json; значение уже заполнено и не требует изменения.",
                "json",
            ),
            "merchant_id": _field(
                "Логин продавца (userName)",
                "API-логин магазина из документов или личного кабинета Сбера. "
                "Передаётся в register.do как userName. Обязательное поле; "
                "обычно имеет суффикс -api, но используйте именно выданное значение.",
                "club-api",
            ),
            "token": _field(
                "API-пароль (password)",
                "Секрет для регистрации платежа; в текущем адаптере хранится "
                "под техническим именем token. Обязательное поле. Это НЕ "
                "callback_token и НЕ пароль входа в личный кабинет.",
                secret=True,
            ),
            "callback_token": _field(
                "Ключ callback (callback_token)",
                "Отдельный секрет для проверки контрольной суммы checksum "
                "уведомления. Включите callback-уведомления у банка и "
                "скопируйте симметричный ключ. Обязательное поле; без него "
                "оплата не будет подтверждаться автоматически.",
                secret=True,
            ),
            "return_url": _field(
                "Return URL",
                "Страница, куда покупатель возвращается после оплаты. Это не "
                "webhook: сама страница не подтверждает платёж. Обязательное "
                "поле; укажите публичную страницу клуба или личного кабинета.",
                "https://club.example.ru/pay/return",
            ),
        },
    },
]


def _draft_bank(code, name):
    return {
        "code": code,
        "name": name,
        "supported": False,
        "intro": (
            "ПОДГОТОВКА РЕКВИЗИТОВ — платёжный адаптер ещё не реализован. "
            "Можно сохранить черновик настроек, но выбрать этот банк активным "
            "и принимать через него оплату пока нельзя. Точные названия и "
            "наличие API-полей подтвердите в договоре и документации банка."
        ),
        "fields": {
            "merchant_id": _field(
                "ID продавца / магазина",
                "Черновое поле для идентификатора магазина из договора или "
                "личного кабинета. Не является подтверждением интеграции.",
                "merchant-demo",
            ),
            "terminal_id": _field(
                "ID терминала",
                "Черновое поле для идентификатора терминала, если банк его "
                "выдаёт отдельно. Оставьте пустым, если в документах его нет.",
                "terminal-demo",
            ),
            "api_key": _field(
                "API-ключ / пароль",
                "Черновое поле для секрета платёжного API. Хранится скрыто; "
                "пустое поле сохраняет прежнее значение. Не вставляйте пароль "
                "входа в личный кабинет.",
                secret=True,
            ),
            "callback_token": _field(
                "Секрет callback",
                "Черновое поле для отдельного ключа проверки уведомлений. "
                "Не копируйте сюда API-ключ, если банк выдал другой секрет.",
                secret=True,
            ),
            "notification_url": _field(
                "Notification URL (черновик)",
                "Планируемый адрес уведомлений. До реализации адаптера банк "
                "не сможет подтвердить оплату через FitIntel. " + COMMON_URL_HELP,
                "https://club.example.ru/api/v1/bank/webhook",
            ),
            "return_url": _field(
                "Return URL (черновик)",
                "Планируемая страница возврата покупателя после оплаты; не "
                "заменяет серверное уведомление и не подтверждает платёж.",
                "https://club.example.ru/pay/return",
            ),
        },
    }


BANKS.extend([
    _draft_bank("vtb", "ВТБ"),
    _draft_bank("alfa", "Альфа-Банк"),
    _draft_bank("psb", "ПСБ"),
])
BANK_BY_CODE = {bank["code"]: bank for bank in BANKS}


class _Get(QThread):
    done = pyqtSignal(dict)
    fail = pyqtSignal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        try:
            response = self.api.session.get(
                self.api._url("/server-settings/bank-config"), timeout=20)
            response.raise_for_status()
            self.done.emit(response.json())
        except Exception as exc:
            self.fail.emit(str(exc))


class BankSettingsTab(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._edits = {}
        self._clear = {}
        self._loaded = False
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("Банки и интернет-эквайринг")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)
        explanation = QLabel(
            "Настройки сохраняются на сервере и применяются без перезапуска. "
            "Секреты не загружаются обратно и не показываются на экране. "
            "Доступ к этому экрану выдаётся в «Экраны ролей» → «Банки»."
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)

        active_row = QHBoxLayout()
        active_row.addWidget(QLabel("Активный банк для новых платежей:"))
        self.active = QComboBox()
        self.active.addItem("Не выбран — банковская оплата отключена", "")
        self.active.addItem("Т-Банк", "tinkoff")
        self.active.addItem("Сбербанк", "sber")
        active_row.addWidget(self.active)
        save = QPushButton("Сохранить настройки банков")
        save.setStyleSheet(
            "QPushButton { background: #10b981; color: white; border: none; "
            "border-radius: 6px; padding: 9px 18px; font-weight: 600; }")
        save.clicked.connect(self._save)
        active_row.addWidget(save)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        active_row.addWidget(refresh)
        active_row.addStretch()
        root.addLayout(active_row)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.status = QLabel("Загрузка настроек…")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def refresh(self):
        self._loaded = False
        self.status.setText("Загрузка настроек…")
        self._get = _Get(self.api)
        self._get.done.connect(self._on_loaded)
        self._get.fail.connect(self._on_error)
        self._get.start()

    def _on_error(self, message):
        self.status.setText("Не загружено: " + message)
        self.status.setStyleSheet("color: #b91c1c;")

    def _on_loaded(self, data):
        self._edits = {}
        self._clear = {}
        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()

        active = data.get("active") or ""
        index = self.active.findData(active)
        self.active.setCurrentIndex(index if index >= 0 else 0)
        providers = data.get("providers") or {}
        for bank in BANKS:
            code = bank["code"]
            saved = providers.get(code) or {}
            self.tabs.addTab(self._bank_page(bank, saved), bank["name"])
        self._loaded = True
        self.status.setText(
            "Готово. После сохранения проверьте тестовый платёж в банке; "
            "успешное сохранение реквизитов само по себе не подтверждает оплату."
        )
        self.status.setStyleSheet("color: #475569;")

    def _bank_page(self, bank, saved):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        layout = QVBoxLayout(host)
        intro = QLabel(bank["intro"])
        intro.setWordWrap(True)
        intro.setStyleSheet(
            "padding: 10px; border-radius: 6px; "
            + ("background: #ecfdf5;" if bank["supported"] else "background: #fff7ed;"))
        layout.addWidget(intro)

        if bank["supported"]:
            webhook_box = QGroupBox("Адрес для callback/webhook в кабинете банка")
            webhook_form = QFormLayout(webhook_box)
            webhook = QLineEdit(self.api.base_url.rstrip("/") + "/bank/webhook")
            webhook.setReadOnly(True)
            webhook.setToolTip("Скопируйте этот адрес в настройки уведомлений банка")
            webhook_form.addRow("POST/GET URL:", webhook)
            layout.addWidget(webhook_box)

        fields_box = QGroupBox("Реквизиты и описание каждого поля")
        form = QFormLayout(fields_box)
        form.setVerticalSpacing(10)
        saved_fields = saved.get("fields") or {}
        code = bank["code"]
        self._edits[code] = {}
        self._clear[code] = {}
        for key, spec in bank["fields"].items():
            meta = saved_fields.get(key) or {}
            edit = QLineEdit()
            edit.setMinimumWidth(360)
            edit.setText(str(meta.get("value") or ""))
            if spec["secret"]:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
                edit.setPlaceholderText(
                    "Секрет сохранён — пусто означает «не менять»"
                    if meta.get("is_set") else "Введите секрет")
                clear = QCheckBox("Очистить сохранённый секрет")
                clear.setEnabled(bool(meta.get("is_set")))
                self._clear[code][key] = clear
                form.addRow(spec["label"] + ":", edit)
                form.addRow("", clear)
            else:
                form.addRow(spec["label"] + ":", edit)
            help_label = QLabel(spec["help"])
            help_label.setWordWrap(True)
            help_label.setStyleSheet("color: #64748b; font-size: 12px;")
            form.addRow("", help_label)
            self._edits[code][key] = edit
        layout.addWidget(fields_box)
        layout.addStretch()
        scroll.setWidget(host)
        return scroll

    def _save(self):
        if not self._loaded:
            QMessageBox.warning(self, "Банки", "Дождитесь загрузки настроек")
            return
        providers = {}
        for code, fields in self._edits.items():
            values = {}
            for key, edit in fields.items():
                spec = BANK_BY_CODE[code]["fields"][key]
                text = edit.text().strip()
                if spec["secret"]:
                    if self._clear[code][key].isChecked():
                        values[key] = None
                    elif text:
                        values[key] = text
                else:
                    values[key] = text
            providers[code] = values
        payload = {"active": self.active.currentData(), "providers": providers}
        try:
            response = self.api.session.put(
                self.api._url("/server-settings/bank-config"),
                json=payload,
                timeout=20,
            )
            if response.status_code != 200:
                try:
                    detail = response.json().get("detail", response.text)
                except Exception:
                    detail = response.text
                QMessageBox.warning(self, "Не сохранено", f"{response.status_code}: {detail}")
                return
            QMessageBox.information(
                self, "Банки",
                "Настройки сохранены. Секреты в сообщении и на экране не отображаются.\n"
                "Теперь проверьте тестовый платёж и уведомление банка.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))
