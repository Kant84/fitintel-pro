import io

# --- devices_tab: Discover + Добавить устройство ---
p = "windows/devices_tab.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    "from api import ApiClient",
    "from PyQt6.QtWidgets import QMessageBox\n\nfrom api import ApiClient\nfrom windows.form_dialog import FormDialog")
src = src.replace(
    '        btn = QPushButton("Обновить")',
    '''        b_disc = QPushButton("Найти устройства")
        b_disc.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_disc.clicked.connect(self._discover)
        row.addWidget(b_disc)
        b_add = QPushButton("Добавить вручную")
        b_add.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_add.clicked.connect(self._add)
        row.addWidget(b_add)
        btn = QPushButton("Обновить")''')
src = src.replace(
    "    def _on_error(self, msg: str):",
    '''    def _driver_options(self):
        return [(str(d.get("package") or d.get("name")), str(d.get("id") or d.get("driver_id") or d.get("package")))
                for d in getattr(self, "_drivers", [])]

    def _discover(self):
        opts = self._driver_options()
        if not opts:
            QMessageBox.warning(self, "Нет драйверов", "Сначала установите драйвер (DAL)")
            return
        dlg = FormDialog("Поиск устройств", [("driver_id", "Драйвер *", "combo", opts)], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        try:
            r = self.api.session.post(self.api._url("/dal/devices/discover"),
                                      json={"driver_id": dlg.values()["driver_id"]})
            r.raise_for_status()
            res = r.json()
            QMessageBox.information(self, "Поиск завершён", str(res)[:300])
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка поиска", str(e))

    def _add(self):
        opts = self._driver_options()
        if not opts:
            QMessageBox.warning(self, "Нет драйверов", "Сначала установите драйвер (DAL)")
            return
        dlg = FormDialog("Новое устройство", [
            ("driver_id", "Драйвер *", "combo", opts),
            ("name", "Название *"),
            ("connection_string", "Подключение (IP/COM/URL) *"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["name"] or not v["connection_string"]:
            QMessageBox.warning(self, "Ошибка", "Заполните название и подключение")
            return
        try:
            r = self.api.session.post(self.api._url("/dal/devices"), json=v)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):''')
src = src.replace(
    "    def _on_loaded(self, devices: list, drivers: list):",
    "    def _on_loaded(self, devices: list, drivers: list):\n        self._drivers = drivers")
io.open(p, "w", encoding="utf-8").write(src)
print("devices_tab PATCHED")

# --- users_tab: создать пользователя ---
p = "windows/users_tab.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    "from api import ApiClient",
    "from PyQt6.QtWidgets import QMessageBox\n\nfrom api import ApiClient\nfrom windows.form_dialog import FormDialog")
src = src.replace(
    '        btn = QPushButton("Обновить")',
    '''        b_add = QPushButton("Создать пользователя")
        b_add.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_add.clicked.connect(self._add)
        row.addWidget(b_add)
        btn = QPushButton("Обновить")''')
src = src.replace(
    "    def _on_error(self, msg: str):",
    '''    def _add(self):
        dlg = FormDialog("Новый пользователь", [
            ("username", "Логин *"),
            ("email", "Email *"),
            ("password", "Пароль *"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["username"] or not v["password"]:
            QMessageBox.warning(self, "Ошибка", "Логин и пароль обязательны")
            return
        try:
            r = self.api.session.post(self.api._url("/users/"), json=v)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):''')
io.open(p, "w", encoding="utf-8").write(src)
print("users_tab PATCHED")

# --- documents_tab: сгенерировать документ ---
p = "windows/documents_tab.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    "from api import ApiClient",
    "from PyQt6.QtWidgets import QMessageBox\n\nfrom api import ApiClient\nfrom windows.form_dialog import FormDialog")
src = src.replace(
    "            self.finished.emit(docs, tpls, cmap)",
    "            self.finished.emit(docs, tpls, cmap)")
src = src.replace(
    '        btn = QPushButton("Обновить")',
    '''        b_gen = QPushButton("Сгенерировать")
        b_gen.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_gen.clicked.connect(self._generate)
        row.addWidget(b_gen)
        btn = QPushButton("Обновить")''')
src = src.replace(
    "    def _on_loaded(self, docs: list, tpls: list, cmap: dict):",
    "    def _on_loaded(self, docs: list, tpls: list, cmap: dict):\n        self._tpls = tpls\n        self._cmap = cmap")
src = src.replace(
    "    def _on_error(self, msg: str):",
    '''    def _generate(self):
        tpls = getattr(self, "_tpls", [])
        cmap = getattr(self, "_cmap", {})
        if not tpls or not cmap:
            QMessageBox.warning(self, "Нет данных", "Нужны шаблоны и клиенты")
            return
        dlg = FormDialog("Новый документ", [
            ("template", "Шаблон *", "combo",
             [(t.get("name", t.get("code")), (t.get("template_id"), t.get("code"))) for t in tpls]),
            ("client_id", "Клиент *", "combo",
             [(v, k) for k, v in list(cmap.items())[:200]]),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        tpl_id, tpl_code = v["template"]
        payload = {"type": tpl_code, "client_id": v["client_id"], "template_id": tpl_id}
        try:
            r = self.api.session.post(self.api._url("/documents"), json=payload)
            r.raise_for_status()
            QMessageBox.information(self, "Готово", "Документ создан")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):''')
io.open(p, "w", encoding="utf-8").write(src)
print("documents_tab PATCHED")
