# -*- coding: utf-8 -*-
"""Корзина: восстановление удалённых клиентов/пользователей/тарифов/шаблонов/зон."""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QComboBox)
from PyQt6.QtCore import Qt


class TrashDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Корзина (восстановление удалённого, 30 дней)")
        self.resize(720, 480)
        v = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Сущность:"))
        self.cmb = QComboBox()
        for label, code in [("Все", ""), ("Клиенты", "clients"), ("Пользователи", "users"),
                            ("Тарифы", "tariffs"), ("Шаблоны документов", "document_templates"),
                            ("Музыкальные зоны", "music_zones")]:
            self.cmb.addItem(label, code)
        self.cmb.currentIndexChanged.connect(self.reload)
        bar.addWidget(self.cmb)
        b_r = QPushButton("Обновить")
        b_r.clicked.connect(self.reload)
        bar.addWidget(b_r)
        bar.addStretch(1)
        v.addLayout(bar)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Сущность", "Название", "Удалён", ""])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        v.addWidget(self.table)
        self.reload()

    def reload(self):
        try:
            r = self.api.session.get(self.api._url("/trash"),
                                     params={"entity": self.cmb.currentData() or ""},
                                     timeout=15)
            r.raise_for_status()
            items = r.json().get("items", [])
        except Exception as e:
            QMessageBox.warning(self, "Корзина", str(e)[:200])
            return
        self.table.setRowCount(len(items))
        self._ids = []
        for i, it in enumerate(items):
            self._ids.append(it["id"])
            self.table.setItem(i, 0, QTableWidgetItem(it["entity"]))
            self.table.setItem(i, 1, QTableWidgetItem(it["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(it["deleted_at"])[:19].replace("T", " ")))
            b = QPushButton("Восстановить")
            b.clicked.connect(lambda _c, sid=it["id"]: self.restore(sid))
            self.table.setCellWidget(i, 3, b)

    def restore(self, sid):
        try:
            r = self.api.session.post(self.api._url("/trash/%s/restore" % sid), timeout=20)
            r.raise_for_status()
            QMessageBox.information(self, "Корзина", "Восстановлено: " + r.json().get("restored", ""))
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Корзина", str(e)[:200])
