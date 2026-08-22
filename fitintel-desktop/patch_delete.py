import io

p = "windows/clients_tab.py"
src = io.open(p, encoding="utf-8").read()

src = src.replace(
    '''        b_deact = self._btn("⊘ Деактивировать", "#fee2e2", "#b91c1c")
        b_deact.clicked.connect(self._deactivate)
        row.addWidget(b_deact)''',
    '''        b_deact = self._btn("⊘ Деактивировать", "#fee2e2", "#b91c1c")
        b_deact.clicked.connect(self._deactivate)
        row.addWidget(b_deact)
        b_del = self._btn("🗑 Удалить", "#dc2626", "white")
        b_del.clicked.connect(self._delete)
        row.addWidget(b_del)''')

src = src.replace(
    "    def _on_error(self, msg: str):",
    '''    def _delete(self):
        c = self._selected_client()
        if not c:
            return
        reply = QMessageBox.warning(
            self, "Удаление клиента",
            f"УДАЛИТЬ клиента {self._fio(c)} безвозвратно?\\n\\nЭто действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api.delete_client(str(c["id"]))
            try:
                from app_logging import log as _log
                _log.info("Удалён клиент %s (%s)", self._fio(c), c.get("id"))
            except Exception:
                pass
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def _on_error(self, msg: str):''')

io.open(p, "w", encoding="utf-8").write(src)
print("clients_tab PATCHED")
