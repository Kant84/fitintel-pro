"""
Путь в проекте: desktop/fiscal_settings_dialog.py
PyQt6 окно настройки касс, банков, СБП и 1С для администратора фитнес-клуба.
Можно запустить отдельно или встроить в главное окно.
"""
import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
    QMessageBox, QTextEdit, QFormLayout, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

API_BASE = "http://localhost:8001/api/v1"


class FiscalSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки касс, банков и бухгалтерии")
        self.setMinimumSize(700, 550)
        self._init_ui()
        self._load_current()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # === Вкладка 1: Кассы (ФР) ===
        self.tab_printers = QWidget()
        self._init_printers_tab()
        self.tabs.addTab(self.tab_printers, "🖨️ Кассы (ФР)")

        # === Вкладка 2: Банки ===
        self.tab_banks = QWidget()
        self._init_banks_tab()
        self.tabs.addTab(self.tab_banks, "💳 Банки / Эквайринг")

        # === Вкладка 3: СБП / Рекурренты ===
        self.tab_sbp = QWidget()
        self._init_sbp_tab()
        self.tabs.addTab(self.tab_sbp, "📱 СБП и Подписки")

        # === Вкладка 4: 1С / Бухгалтерия ===
        self.tab_1c = QWidget()
        self._init_1c_tab()
        self.tabs.addTab(self.tab_1c, "📊 Бухгалтерия / 1С")

        layout.addWidget(self.tabs)

        # Кнопки внизу
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("🧪 Тест соединения")
        self.btn_test.clicked.connect(self.run_test)
        self.btn_save = QPushButton("💾 Сохранить настройки")
        self.btn_save.clicked.connect(self.save_settings)
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_test)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        layout.addWidget(self.log)

        self.setLayout(layout)

    # -----------------------------------------------------------------
    # КАССЫ
    # -----------------------------------------------------------------
    def _init_printers_tab(self):
        layout = QVBoxLayout()

        self.combo_printer = QComboBox()
        self.combo_printer.addItems(["АТОЛ (ДТО 10)", "Штрих-М (Web)", "Эвотор (Cloud)", "Меркурий (Web)"])
        self.combo_printer.currentIndexChanged.connect(self._on_printer_changed)

        layout.addWidget(QLabel("<b>Активная касса:</b>"))
        layout.addWidget(self.combo_printer)

        # АТОЛ
        self.group_atol = QGroupBox("Настройки АТОЛ")
        f = QFormLayout()
        self.atol_url = QLineEdit("http://127.0.0.1:16732")
        self.atol_auth = QLineEdit()
        self.atol_auth.setPlaceholderText("логин:пароль (если Basic Auth)")
        f.addRow("URL ДТО 10:", self.atol_url)
        f.addRow("Авторизация:", self.atol_auth)
        self.group_atol.setLayout(f)
        layout.addWidget(self.group_atol)

        # Штрих-М
        self.group_shtrih = QGroupBox("Настройки Штрих-М")
        f = QFormLayout()
        self.shtrih_url = QLineEdit("http://127.0.0.1:8080")
        self.shtrih_pass = QLineEdit("30")
        f.addRow("URL Web-сервера:", self.shtrih_url)
        f.addRow("Пароль кассира:", self.shtrih_pass)
        self.group_shtrih.setLayout(f)
        self.group_shtrih.setVisible(False)
        layout.addWidget(self.group_shtrih)

        # Эвотор
        self.group_evotor = QGroupBox("Настройки Эвотор")
        f = QFormLayout()
        self.evotor_token = QLineEdit()
        self.evotor_token.setPlaceholderText("API-токен из личного кабинета Эвотор")
        f.addRow("Токен:", self.evotor_token)
        self.group_evotor.setLayout(f)
        self.group_evotor.setVisible(False)
        layout.addWidget(self.group_evotor)

        # Меркурий
        self.group_mercury = QGroupBox("Настройки Меркурий")
        f = QFormLayout()
        self.mercury_url = QLineEdit("http://127.0.0.1:5000")
        self.mercury_key = QLineEdit()
        self.mercury_key.setPlaceholderText("API-ключ")
        f.addRow("URL:", self.mercury_url)
        f.addRow("API Key:", self.mercury_key)
        self.group_mercury.setLayout(f)
        self.group_mercury.setVisible(False)
        layout.addWidget(self.group_mercury)

        layout.addStretch()
        self.tab_printers.setLayout(layout)

    def _on_printer_changed(self, idx: int):
        self.group_atol.setVisible(idx == 0)
        self.group_shtrih.setVisible(idx == 1)
        self.group_evotor.setVisible(idx == 2)
        self.group_mercury.setVisible(idx == 3)

    # -----------------------------------------------------------------
    # БАНКИ
    # -----------------------------------------------------------------
    def _init_banks_tab(self):
        layout = QVBoxLayout()

        self.combo_bank = QComboBox()
        self.combo_bank.addItems(["Сбербанк", "Тинькофф", "Райффайзен"])
        self.combo_bank.currentIndexChanged.connect(self._on_bank_changed)
        layout.addWidget(QLabel("<b>Активный банк:</b>"))
        layout.addWidget(self.combo_bank)

        # Сбер
        self.group_sber = QGroupBox("Сбербанк")
        f = QFormLayout()
        self.sber_mode = QComboBox()
        self.sber_mode.addItems(["Эмуляция (mock)", "JSON API", "DLL (sbrf.dll)"])
        self.sber_dll = QLineEdit()
        self.sber_dll.setPlaceholderText("C:\Sber\sbrf.dll")
        self.sber_merch = QLineEdit()
        self.sber_token = QLineEdit()
        f.addRow("Режим:", self.sber_mode)
        f.addRow("Путь к DLL:", self.sber_dll)
        f.addRow("Merchant ID:", self.sber_merch)
        f.addRow("Token:", self.sber_token)
        self.group_sber.setLayout(f)
        layout.addWidget(self.group_sber)

        # Тинькофф
        self.group_tinkoff = QGroupBox("Тинькофф")
        f = QFormLayout()
        self.tinkoff_key = QLineEdit()
        self.tinkoff_pass = QLineEdit()
        self.tinkoff_pass.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow("TerminalKey:", self.tinkoff_key)
        f.addRow("Пароль:", self.tinkoff_pass)
        self.group_tinkoff.setLayout(f)
        self.group_tinkoff.setVisible(False)
        layout.addWidget(self.group_tinkoff)

        # Райффайзен
        self.group_raiff = QGroupBox("Райффайзен")
        f = QFormLayout()
        self.raiff_id = QLineEdit()
        self.raiff_key = QLineEdit()
        self.raiff_key.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow("Merchant ID:", self.raiff_id)
        f.addRow("Secret Key:", self.raiff_key)
        self.group_raiff.setLayout(f)
        self.group_raiff.setVisible(False)
        layout.addWidget(self.group_raiff)

        layout.addStretch()
        self.tab_banks.setLayout(layout)

    def _on_bank_changed(self, idx: int):
        self.group_sber.setVisible(idx == 0)
        self.group_tinkoff.setVisible(idx == 1)
        self.group_raiff.setVisible(idx == 2)

    # -----------------------------------------------------------------
    # СБП
    # -----------------------------------------------------------------
    def _init_sbp_tab(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Настройки СБП и рекуррентных платежей</b>"))

        self.sbp_mock = QComboBox()
        self.sbp_mock.addItems(["Режим эмуляции (mock)", "Реальный API Т-Банк", "Реальный API Сбер"])
        layout.addWidget(QLabel("Режим работы:"))
        layout.addWidget(self.sbp_mock)

        f = QFormLayout()
        self.sbp_terminal = QLineEdit()
        self.sbp_password = QLineEdit()
        self.sbp_password.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow("TerminalKey / ID:", self.sbp_terminal)
        f.addRow("Пароль / Secret:", self.sbp_password)
        layout.addLayout(f)

        layout.addWidget(QLabel("Рекурренты (автопродление абонементов):"))
        self.chk_recurrent = QComboBox()
        self.chk_recurrent.addItems(["Включены", "Выключены"])
        layout.addWidget(self.chk_recurrent)

        layout.addStretch()
        self.tab_sbp.setLayout(layout)

    # -----------------------------------------------------------------
    # 1С / БУХГАЛТЕРИЯ
    # -----------------------------------------------------------------
    def _init_1c_tab(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Режим бухгалтерии</b>"))

        self.combo_acc = QComboBox()
        self.combo_acc.addItems([
            "Внутренняя бухгалтерия FitIntel (не требует 1С)",
            "Обмен с 1С через файлы (CommerceML)",
            "Обмен с 1С через OData (прямое подключение)"
        ])
        self.combo_acc.currentIndexChanged.connect(self._on_acc_changed)
        layout.addWidget(self.combo_acc)

        self.group_1c_file = QGroupBox("Обмен файлами с 1С")
        f = QFormLayout()
        self.onec_path = QLineEdit("./1c_exchange")
        f.addRow("Папка обмена:", self.onec_path)
        self.group_1c_file.setLayout(f)
        layout.addWidget(self.group_1c_file)

        self.group_1c_http = QGroupBox("Прямое подключение к 1С (OData)")
        f = QFormLayout()
        self.onec_url = QLineEdit("http://localhost:8080/buh/odata/standard.odata")
        self.onec_user = QLineEdit("Администратор")
        self.onec_pwd = QLineEdit()
        self.onec_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow("URL 1С:", self.onec_url)
        f.addRow("Пользователь:", self.onec_user)
        f.addRow("Пароль:", self.onec_pwd)
        self.group_1c_http.setLayout(f)
        self.group_1c_http.setVisible(False)
        layout.addWidget(self.group_1c_http)

        layout.addWidget(QLabel("<b>Текущий отчет (пример):</b>"))
        self.acc_report = QTextEdit()
        self.acc_report.setPlaceholderText("Нажмите 'Тест соединения' для получения ОСВ...")
        self.acc_report.setMaximumHeight(150)
        layout.addWidget(self.acc_report)

        layout.addStretch()
        self.tab_1c.setLayout(layout)

    def _on_acc_changed(self, idx: int):
        self.group_1c_file.setVisible(idx == 1)
        self.group_1c_http.setVisible(idx == 2)

    # -----------------------------------------------------------------
    # ЛОГИКА
    # -----------------------------------------------------------------
    def _load_current(self):
        """Загрузить текущие настройки с бэкенда (если доступен)."""
        try:
            r = requests.get(f"{API_BASE}/fiscal/printers", timeout=3)
            if r.status_code == 200:
                data = r.json()
                self.log.append(f"Загружено: активная касса = {data.get('active')}")
        except Exception as e:
            self.log.append(f"Бэкенд недоступен ({e}). Работаем офлайн.")

    def run_test(self):
        self.log.clear()
        tab = self.tabs.currentIndex()
        try:
            if tab == 0:
                # Тест кассы
                r = requests.get(f"{API_BASE}/fiscal/printers/health", timeout=5)
                self.log.append(str(r.json()))
            elif tab == 1:
                r = requests.get(f"{API_BASE}/fiscal/banks", timeout=5)
                self.log.append(str(r.json()))
            elif tab == 2:
                self.log.append("СБП: режим эмуляции активен. QR будет генерироваться локально.")
            elif tab == 3:
                # Тест внутренней бухгалтерии
                period = "2026-06"
                r = requests.get(f"{API_BASE}/accounting/balance-sheet/{period}", timeout=5)
                self.acc_report.setText(str(r.json()))
                self.log.append("Баланс получен.")
        except Exception as e:
            self.log.append(f"Ошибка теста: {e}")

    def save_settings(self):
        """Отправить настройки на бэкенд."""
        self.log.append("Сохранение...")
        # В реальном ПО здесь POST /api/v1/settings
        QMessageBox.information(self, "Сохранено", "Настройки сохранены (демо-режим).")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = FiscalSettingsDialog()
    dlg.show()
    sys.exit(app.exec())
