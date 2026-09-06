"""FitIntel Pro — Connections Manager (1C-style)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit,
    QFormLayout, QComboBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
import json, os

CONNECTIONS_FILE = "connections.json"

class ConnectionDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Параметры подключения")
        self.setMinimumWidth(450)
        self.data = data or {}
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Мой клуб")
        form.addRow("Название:", self.ed_name)

        self.cmb_type = QComboBox()
        self.cmb_type.addItem("Локальный сервер", "local")
        self.cmb_type.addItem("Веб-сервер (URL)", "web")
        self.cmb_type.addItem("Сервер приложений (кластер)", "cluster")
        self.cmb_type.currentIndexChanged.connect(self._type_changed)
        form.addRow("Тип расположения:", self.cmb_type)

        self.grp_local = QGroupBox()
        fl = QFormLayout(self.grp_local)
        self.ed_local_path = QLineEdit()
        self.ed_local_path.setPlaceholderText("C:\\Users\\...\\FitIntel AI\\.env")
        fl.addRow("Путь к .env:", self.ed_local_path)
        form.addRow(self.grp_local)

        self.grp_web = QGroupBox()
        fl = QFormLayout(self.grp_web)
        self.ed_web_url = QLineEdit()
        self.ed_web_url.setPlaceholderText("http://localhost:8001/api/v1")
        fl.addRow("Адрес API:", self.ed_web_url)
        self.ed_web_login = QLineEdit()
        fl.addRow("Логин:", self.ed_web_login)
        self.ed_web_pass = QLineEdit()
        self.ed_web_pass.setEchoMode(QLineEdit.EchoMode.Password)
        fl.addRow("Пароль:", self.ed_web_pass)
        form.addRow(self.grp_web)

        self.grp_cluster = QGroupBox()
        fl = QFormLayout(self.grp_cluster)
        self.ed_db_host = QLineEdit()
        self.ed_db_host.setPlaceholderText("localhost")
        fl.addRow("Хост БД:", self.ed_db_host)
        self.ed_db_port = QLineEdit()
        self.ed_db_port.setPlaceholderText("5432")
        fl.addRow("Порт БД:", self.ed_db_port)
        self.ed_db_name = QLineEdit()
        self.ed_db_name.setPlaceholderText("fitnexus")
        fl.addRow("Имя базы:", self.ed_db_name)
        self.ed_db_user = QLineEdit()
        fl.addRow("Пользователь:", self.ed_db_user)
        self.ed_db_pass = QLineEdit()
        self.ed_db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        fl.addRow("Пароль:", self.ed_db_pass)
        form.addRow(self.grp_cluster)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_ok = QPushButton("Сохранить")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def _type_changed(self):
        t = self.cmb_type.currentData()
        self.grp_local.setVisible(t == "local")
        self.grp_web.setVisible(t == "web")
        self.grp_cluster.setVisible(t == "cluster")

    def _load_data(self):
        self.ed_name.setText(self.data.get("name", ""))
        idx = self.cmb_type.findData(self.data.get("type", "web"))
        if idx >= 0:
            self.cmb_type.setCurrentIndex(idx)
        self.ed_local_path.setText(self.data.get("local_path", ""))
        self.ed_web_url.setText(self.data.get("web_url", "http://localhost:8001/api/v1"))
        self.ed_web_login.setText(self.data.get("web_login", ""))
        self.ed_web_pass.setText(self.data.get("web_pass", ""))
        self.ed_db_host.setText(self.data.get("db_host", "localhost"))
        self.ed_db_port.setText(str(self.data.get("db_port", "5432")))
        self.ed_db_name.setText(self.data.get("db_name", "fitnexus"))
        self.ed_db_user.setText(self.data.get("db_user", "postgres"))
        self.ed_db_pass.setText(self.data.get("db_pass", ""))
        self._type_changed()

    def get_data(self):
        return {
            "name": self.ed_name.text(),
            "type": self.cmb_type.currentData(),
            "local_path": self.ed_local_path.text(),
            "web_url": self.ed_web_url.text(),
            "web_login": self.ed_web_login.text(),
            "web_pass": self.ed_web_pass.text(),
            "db_host": self.ed_db_host.text(),
            "db_port": self.ed_db_port.text(),
            "db_name": self.ed_db_name.text(),
            "db_user": self.ed_db_user.text(),
            "db_pass": self.ed_db_pass.text(),
        }


class ConnectionsTab(QWidget):
    def __init__(self, api=None, main_window=None):
        super().__init__()
        self.api = api
        self.mw = main_window
        self._build_ui()
        self._load_list()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        left = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._edit)
        left.addWidget(QLabel("Информационные базы:"))
        left.addWidget(self.list_widget)

        right = QVBoxLayout()
        right.setSpacing(8)

        btn_add = QPushButton("Добавить...")
        btn_add.clicked.connect(self._add)
        right.addWidget(btn_add)

        btn_edit = QPushButton("Изменить...")
        btn_edit.clicked.connect(self._edit)
        right.addWidget(btn_edit)

        btn_del = QPushButton("Удалить")
        btn_del.clicked.connect(self._delete)
        right.addWidget(btn_del)

        right.addSpacing(20)

        btn_connect = QPushButton("Подключить")
        btn_connect.setStyleSheet("background: #059669; color: white; padding: 10px; font-weight: 600;")
        btn_connect.clicked.connect(self._connect)
        right.addWidget(btn_connect)

        btn_settings = QPushButton("Настройка...")
        btn_settings.clicked.connect(self._settings)
        right.addWidget(btn_settings)

        right.addStretch()

        layout.addLayout(left, 3)
        layout.addLayout(right, 1)

    def _load_list(self):
        self.list_widget.clear()
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
            self._save()
        for c in self.connections:
            item = QListWidgetItem(c["name"])
            item.setData(Qt.ItemDataRole.UserRole, c)
            self.list_widget.addItem(item)

    def _save(self):
        with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.connections, f, ensure_ascii=False, indent=2)

    def _add(self):
        dlg = ConnectionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.connections.append(data)
            self._save()
            self._load_list()

    def _edit(self):
        idx = self.list_widget.currentRow()
        if idx < 0:
            QMessageBox.warning(self, "Внимание", "Выберите базу")
            return
        data = self.connections[idx]
        dlg = ConnectionDialog(self, data)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.connections[idx] = dlg.get_data()
            self._save()
            self._load_list()

    def _delete(self):
        idx = self.list_widget.currentRow()
        if idx < 0:
            return
        if QMessageBox.question(self, "Удаление", f"Удалить '{self.connections[idx]['name']}'?") == QMessageBox.StandardButton.Yes:
            del self.connections[idx]
            self._save()
            self._load_list()

    def _connect(self):
        idx = self.list_widget.currentRow()
        if idx < 0:
            QMessageBox.warning(self, "Внимание", "Выберите базу для подключения")
            return
        conn = self.connections[idx]
        try:
            cfg = {}
            if os.path.exists("client_settings.json"):
                cfg = json.load(open("client_settings.json", encoding="utf-8"))
            cfg["api_base"] = conn.get("web_url", "http://localhost:8001/api/v1")
            cfg["saved_login"] = conn.get("web_login", "")
            cfg["saved_password"] = conn.get("web_pass", "")
            with open("client_settings.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Подключение", f"Профиль '{conn['name']}' активирован.\nПерезапустите клиент.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _settings(self):
        QMessageBox.information(self, "Настройка", "Дополнительные параметры подключения.")