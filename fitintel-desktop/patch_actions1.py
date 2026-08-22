import io

# --- visits_tab: кнопка "Ручной вход" ---
p = "windows/visits_tab.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    "from api import ApiClient",
    "from datetime import datetime\nfrom PyQt6.QtWidgets import QMessageBox\n\nfrom api import ApiClient\nfrom windows.form_dialog import FormDialog")
src = src.replace(
    '        btn = QPushButton("Обновить")',
    '''        btn_in = QPushButton("Ручной вход")
        btn_in.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_in.clicked.connect(self._checkin)
        cards.addWidget(btn_in)
        btn = QPushButton("Обновить")''')
src = src.replace(
    "    def _on_error(self, msg: str):",
    '''    def _checkin(self):
        if not self._cmap:
            QMessageBox.warning(self, "Нет данных", "Список клиентов пуст")
            return
        options = [(f"{v[0]} ({v[1]})", k) for k, v in list(self._cmap.items())[:200]]
        dlg = FormDialog("Ручной вход клиента", [
            ("client_id", "Клиент *", "combo", options),
            ("access_method", "Способ", "combo",
             [("Ручной (ресепшен)", "manual"), ("Карта", "card"), ("QR", "qr"), ("Face ID", "face")]),
            ("zone", "Зона", "text", "main"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        payload = {"client_id": v["client_id"],
                   "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "access_method": v["access_method"], "zone": v["zone"] or "main"}
        try:
            r = self.api.session.post(self.api._url("/visits/manual"), json=payload)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка входа", str(e))

    def _on_error(self, msg: str):''')
io.open(p, "w", encoding="utf-8").write(src)
print("visits_tab PATCHED")

# --- tariffs_tab: кнопка "Создать тариф" ---
p = "windows/tariffs_tab.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    "from api import ApiClient",
    "from PyQt6.QtWidgets import QMessageBox\n\nfrom api import ApiClient\nfrom windows.form_dialog import FormDialog")
src = src.replace(
    '        btn = QPushButton("Обновить")',
    '''        btn_add = QPushButton("Создать тариф")
        btn_add.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_add.clicked.connect(self._add)
        row.addWidget(btn_add)
        btn = QPushButton("Обновить")''')
src = src.replace(
    "    def _on_error(self, msg: str):",
    '''    def _add(self):
        dlg = FormDialog("Новый тариф", [
            ("code", "Код (A-Z, 0-9, _) *"),
            ("name", "Название *"),
            ("price", "Цена *", "text", "1000"),
            ("duration_days", "Дней действия *", "text", "30"),
            ("visit_limit", "Лимит визитов (пусто = без лимита)"),
            ("is_unlimited", "Тип", "combo", [("Лимитированный", False), ("Безлимитный", True)]),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["code"] or not v["name"]:
            QMessageBox.warning(self, "Ошибка", "Код и название обязательны")
            return
        payload = {"code": v["code"].upper(), "name": v["name"],
                   "price": float(v["price"] or 0),
                   "duration_days": int(v["duration_days"] or 30),
                   "is_unlimited": bool(v["is_unlimited"])}
        if v["visit_limit"]:
            payload["visit_limit"] = int(v["visit_limit"])
        try:
            r = self.api.session.post(self.api._url("/tariffs/"), json=payload)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка создания", str(e))

    def _on_error(self, msg: str):''')
io.open(p, "w", encoding="utf-8").write(src)
print("tariffs_tab PATCHED")
