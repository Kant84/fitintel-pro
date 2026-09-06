"""FitIntel Pro — Startup Dialog (1C-style)"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
import json, os

CONNECTIONS_FILE = "connections.json"
SETTINGS_FILE = "client_settings.json"

class StartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FitIntel Pro — Выбор информационной базы")
        self.setMinimumSize(600, 400)
        self.selected_config = None
        self._build_ui()
        self._load_list()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        left = QVBoxLayout()
        left.addWidget(QLabel("Информационные базы:"))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._on_connect)
        left.addWidget(self.list)

        right = QVBoxLayout()
        right.setSpacing(8)

        btn_connect = QPushButton("1. Подключить")
        btn_connect.setStyleSheet("background: #059669; color: white; padding: 10px; font-weight: 600;")
        btn_connect.clicked.connect(self._on_connect)
        right.addWidget(btn_connect)

        btn_add = QPushButton("2. Добавить...")
        btn_add.clicked.connect(self._on_add)
        right.addWidget(btn_add)

        btn_edit = QPushButton("3. Изменить...")
        btn_edit.clicked.connect(self._on_edit)
        right.addWidget(btn_edit)

        btn_del = QPushButton("4. Удалить")
        btn_del.clicked.connect(self._on_delete)
        right.addWidget(btn_del)

        right.addSpacing(20)

        btn_help = QPushButton("? Справка")
        btn_help.clicked.connect(self._on_help)
        right.addWidget(btn_help)

        btn_exit = QPushButton("Выход")
        btn_exit.clicked.connect(self.reject)
        right.addWidget(btn_exit)

        right.addStretch()
        layout.addLayout(left, 3)
        layout.addLayout(right, 1)

    def _load_list(self):
        self.list.clear()
        self.connections = []
        if os.path.exists(CONNECTIONS_FILE):
            with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
                self.connections = json.load(f)
        else:
            self.connections = [{
                "name": "Локальный сервер",
                "type": "web",
                "web_url": "http://localhost:8001/api/v1",
                "web_login": "",
                "web_pass": ""
            }]
            self._save_connections()
        for c in self.connections:
            item = QListWidgetItem(c["name"])
            item.setData(Qt.ItemDataRole.UserRole, c)
            self.list.addItem(item)

    def _save_connections(self):
        with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.connections, f, ensure_ascii=False, indent=2)

    def _on_connect(self):
        idx = self.list.currentRow()
        if idx < 0:
            QMessageBox.warning(self, "Внимание", "Выберите базу для подключения")
            return
        conn = self.connections[idx]
        cfg = {}
        if os.path.exists(SETTINGS_FILE):
            cfg = json.load(open(SETTINGS_FILE, encoding="utf-8"))
        cfg["api_base"] = conn.get("web_url", "http://localhost:8001/api/v1")
        cfg["saved_login"] = conn.get("web_login", "")
        cfg["saved_password"] = conn.get("web_pass", "")
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self.selected_config = cfg
        self.accept()

    def _on_add(self):
        from windows.connections_tab import ConnectionDialog
        dlg = ConnectionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.connections.append(dlg.get_data())
            self._save_connections()
            self._load_list()

    def _on_edit(self):
        from windows.connections_tab import ConnectionDialog
        idx = self.list.currentRow()
        if idx < 0:
            return
        dlg = ConnectionDialog(self, self.connections[idx])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.connections[idx] = dlg.get_data()
            self._save_connections()
            self._load_list()

    def _on_delete(self):
        idx = self.list.currentRow()
        if idx < 0:
            return
        if QMessageBox.question(self, "Удаление", f"Удалить '{self.connections[idx]['name']}'?") == QMessageBox.StandardButton.Yes:
            del self.connections[idx]
            self._save_connections()
            self._load_list()

    def _on_help(self):
        QMessageBox.information(self, "Справка",
            "Инструкция по подключению:\n\n"
            "1. Информационная база — это профиль подключения к серверу FitIntel Pro.\n"
            "   Аналогично списку баз в 1С.\n\n"
            "2. «Локальный сервер» — подключение к серверу на этом компьютере "
            "(http://localhost:8001).\n\n"
            "3. Чтобы добавить новую базу:\n"
            "   • Нажмите «Добавить...»\n"
            "   • Выберите тип:\n"
            "     - Веб-сервер (URL) — для удалённого сервера\n"
            "     - Локальный сервер — если сервер на этом ПК\n"
            "     - Кластер — прямое подключение к PostgreSQL\n"
            "   • Введите адрес, логин и пароль\n"
            "   • Нажмите «Сохранить»\n\n"
            "4. Чтобы переключиться на другую базу:\n"
            "   • Выберите базу в списке\n"
            "   • Нажмите «Подключить»\n"
            "   • Перезапустите программу\n\n"
            "5. Если сервер недоступен — проверьте, запущен ли бэкенд "
            "(uvicorn app.main:app --reload).")