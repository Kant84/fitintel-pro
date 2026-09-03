"""Поиск клиента по ФИО."""
import urllib.request
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                             QListWidget, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ClientSearchDialog(QDialog):
    def __init__(self, clients, parent=None):
        super().__init__(parent)
        self.clients = clients
        self.selected_client = None
        self.setWindowTitle("🔍 Выберите клиента")
        self.resize(500, 350)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #e2e8f0; }
            QLabel { color: #06b6d4; font-size: 14px; font-weight: 600; }
            QListWidget {
                background: #1e293b; border: 1px solid #334155; border-radius: 8px;
                color: #e2e8f0; padding: 8px; font-size: 13px;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #334155; }
            QListWidget::item:selected { background: #ec4899; color: white; }
            QPushButton {
                background: linear-gradient(135deg, #ec4899, #be185d);
                border: none; border-radius: 8px; padding: 10px 24px;
                color: white; font-weight: 600;
            }
            QPushButton:hover { opacity: 0.85; }
        """)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(16, 16, 16, 16)

        hdr = QLabel(f"Найдено клиентов: {len(self.clients)}")
        hdr.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lay.addWidget(hdr)

        sub = QLabel("Выберите нужного клиента из списка:")
        sub.setStyleSheet("color: #94a3b8; font-weight: normal;")
        lay.addWidget(sub)

        self.list_widget = QListWidget()
        for c in self.clients:
            ln = c.get("last_name", "")
            fn = c.get("first_name", "")
            mn = c.get("middle_name", "")
            name = f"{ln} {fn} {mn}".strip()
            phone = c.get("phone", "—")
            cid = c.get("id", "—")
            self.list_widget.addItem(f"{name}  |  📱 {phone}  |  ID: {cid}")
        self.list_widget.setCurrentRow(0)
        lay.addWidget(self.list_widget, 1)

        btn_lay = QHBoxLayout()
        btn_lay.addStretch(1)
        btn_ok = QPushButton("✅ Выбрать")
        btn_ok.clicked.connect(self._on_select)
        btn_lay.addWidget(btn_ok)
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.setStyleSheet("""
            background: linear-gradient(135deg, #475569, #334155);
            border: none; border-radius: 8px; padding: 10px 24px;
            color: white; font-weight: 600;
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_cancel)
        btn_lay.addStretch(1)
        lay.addLayout(btn_lay)

    def _on_select(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.selected_client = self.clients[idx]
            self.accept()
        else:
            QMessageBox.warning(self, "Выбор", "Выберите клиента из списка")


class ClientSearch:
    def __init__(self, tab):
        self.tab = tab
        self._req = tab._req
        self._log = tab._log

    def search(self, query: str):
        query = query.strip()
        if not query:
            QMessageBox.information(self.tab, "Поиск", "Введите ФИО, телефон или ID клиента")
            return None

        if len(query) < 2:
            QMessageBox.information(self.tab, "Поиск", "Введите минимум 2 символа")
            return None

        self._log(self.tab.log, f"🔍 Поиск: '{query}'")

        # Загружаем всех клиентов (API search игнорирует параметр)
        r = self._req("GET", "/clients?limit=200")
        if isinstance(r, dict) and "_err" in r:
            self._log(self.tab.log, f"❌ Ошибка API: {r.get('_err')} — {r.get('_body', '')}")
            QMessageBox.information(self.tab, "Поиск", f"Ошибка сервера: {r.get('_err')}")
            return None

        all_items = r.get("items", []) if isinstance(r, dict) else []
        self._log(self.tab.log, f"📋 Всего клиентов в базе: {len(all_items)}")

        # Фильтруем сами — минимум 3 начальные буквы совпадают
        query_lower = query.lower()
        filtered = []
        for c in all_items:
            ln = c.get("last_name", "").lower()
            fn = c.get("first_name", "").lower()
            mn = c.get("middle_name", "").lower()
            full = f"{ln} {fn} {mn}".strip()
            phone = str(c.get("phone", "")).lower()
            cid = str(c.get("id", "")).lower()

            # Проверяем: запрос должен быть подстрокой ФИО/телефона/ID
            if (query_lower in full or 
                query_lower in phone or 
                query_lower in cid or
                self._fuzzy_match(query_lower, ln) or
                self._fuzzy_match(query_lower, fn) or
                self._fuzzy_match(query_lower, mn)):
                filtered.append(c)

        self._log(self.tab.log, f"🔍 Совпадений: {len(filtered)}")

        if not filtered:
            QMessageBox.information(self.tab, "Поиск", f"Клиенты не найдены по запросу: {query}")
            return None

        if len(filtered) == 1:
            self._log(self.tab.log, "✅ Один результат — выбран автоматически")
            return filtered[0]

        dialog = ClientSearchDialog(filtered, parent=self.tab)
        dialog.exec()
        return dialog.selected_client

    def _fuzzy_match(self, query, text):
        """Проверяет, что первые min(3, len(query)) буквы query совпадают с началом text."""
        if not text:
            return False
        prefix_len = min(3, len(query))
        return text[:prefix_len] == query[:prefix_len]