# -*- coding: utf-8 -*-
"""W15: глобальный аудит доступа к данным (все клиенты)."""
import csv, os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QAbstractItemView, QMessageBox)

ACTS = [("", "Все действия"), ("view", "Просмотр"), ("upload", "Загрузка"),
        ("delete", "Удаление"), ("list", "Список"),
        ("consent_grant", "Согласие выдано"), ("consent_revoke", "Согласие отозвано")]


class AccessAuditTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.ed_client = QLineEdit()
        self.ed_client.setPlaceholderText("ID клиента (пусто = все)")
        self.cb_act = QComboBox()
        for c, n in ACTS:
            self.cb_act.addItem(n, c)
        b = QPushButton("Обновить")
        b.clicked.connect(self.load)
        be = QPushButton("Сохранить CSV")
        be.clicked.connect(self._csv)
        bar.addWidget(QLabel("Клиент:"))
        bar.addWidget(self.ed_client, 1)
        bar.addWidget(self.cb_act)
        bar.addWidget(b)
        bar.addWidget(be)
        lay.addLayout(bar)
        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(
            ["Когда", "Кто", "Действие", "Файл", "Клиент ID", "Результат", "IP"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.tbl, 1)
        lay.addWidget(QLabel("Обращения к фото/документам и события согласий по ВСЕМ клиентам. "
                             "Доступ: superadmin / admin / audit.view."))
        self.load()

    def _get(self, path, params=None):
        r = self.api.session.get(self.api._url(path), params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()

    def load(self):
        try:
            d = self._get("/analytics/w12/access-audit", {
                "limit": 500,
                "client_id": self.ed_client.text().strip() or None,
                "action": self.cb_act.currentData() or None})
            if d.get("error"):
                self.tbl.setRowCount(1)
                self.tbl.setItem(0, 0, QTableWidgetItem("Нет доступа: " + d["error"]))
                return
            items = d.get("items", [])
        except Exception as e:
            items = []
            QMessageBox.warning(self, "Аудит", str(e)[:200])
        ACT = {"view": "Просмотр", "upload": "Загрузка", "delete": "Удаление",
               "list": "Список", "consent_grant": "Согласие выдано",
               "consent_revoke": "Согласие отозвано"}
        self.tbl.setRowCount(len(items))
        for i, r in enumerate(items):
            vals = [str(r.get("created_at") or "")[:19], str(r.get("who") or "—"),
                    ACT.get(r.get("action"), r.get("action") or ""),
                    str(r.get("fname") or "—"), str(r.get("client_id") or "")[:12],
                    str(r.get("result") or ""), str(r.get("ip") or "")]
            for j, v in enumerate(vals):
                self.tbl.setItem(i, j, QTableWidgetItem(v))

    def _csv(self):
        path = os.path.join(os.getcwd(), "export", "access_audit.csv")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([self.tbl.horizontalHeaderItem(c).text() for c in range(self.tbl.columnCount())])
            for r in range(self.tbl.rowCount()):
                w.writerow([(self.tbl.item(r, c).text() if self.tbl.item(r, c) else "")
                            for c in range(self.tbl.columnCount())])
        QMessageBox.information(self, "Экспорт", "Сохранено: " + path)