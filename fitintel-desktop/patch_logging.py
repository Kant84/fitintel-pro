import io

# --- main.py: логирование + excepthook ---
p = "main.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    "from api import ApiClient",
    "from app_logging import log, install_excepthook\nfrom api import ApiClient")
src = src.replace(
    "def main():",
    "def main():\n    install_excepthook()\n    log.info('=== FitIntel Pro Desktop запущен ===')")
src = src.replace(
    "    def on_login_success(user_data: dict, token: str):",
    "    def on_login_success(user_data: dict, token: str):\n"
    "        log.info('Вход выполнен: %s', user_data.get('username', '?'))")
src = src.replace(
    "    sys.exit(app.exec())",
    "    code = app.exec()\n    log.info('=== Клиент завершил работу ===')\n    sys.exit(code)")
io.open(p, "w", encoding="utf-8").write(src)
print("main.py PATCHED")

# --- api/client.py: логирование ошибок HTTP ---
p = "api/client.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    '        self.session.headers.update({"Content-Type": "application/json"})',
    '''        self.session.headers.update({"Content-Type": "application/json"})
        try:
            from app_logging import log as _log
            def _resp_hook(resp, *args, **kwargs):
                if resp.status_code >= 400:
                    _log.warning("%s %s -> %s: %s", resp.request.method, resp.url,
                                 resp.status_code, resp.text[:200])
            self.session.hooks["response"].append(_resp_hook)
        except Exception:
            pass''')
io.open(p, "w", encoding="utf-8").write(src)
print("client.py PATCHED")

# --- login_window.py: запоминание логина/пароля ---
p = "windows/login_window.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace(
    'self.chk_remember = QCheckBox("Запомнить меня")',
    '''self.chk_remember = QCheckBox("Запомнить меня")
        self._load_saved_credentials()''')
src = src.replace(
    "    def _on_success(self, result: dict):",
    '''    def _load_saved_credentials(self):
        try:
            import json as _json
            from pathlib import Path as _P
            st = _json.loads((_P(__file__).parents[1] / "client_settings.json").read_text(encoding="utf-8"))
            if st.get("remember_login"):
                self.edit_login.setText(st.get("saved_login", ""))
                self.edit_pass.setText(st.get("saved_password", ""))
                self.chk_remember.setChecked(True)
        except Exception:
            pass

    def _save_credentials(self):
        try:
            import json as _json
            from pathlib import Path as _P
            path = _P(__file__).parents[1] / "client_settings.json"
            try:
                st = _json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                st = {}
            if self.chk_remember.isChecked():
                st["remember_login"] = True
                st["saved_login"] = self.edit_login.text().strip()
                st["saved_password"] = self.edit_pass.text()
            else:
                st["remember_login"] = False
                st.pop("saved_login", None)
                st.pop("saved_password", None)
            path.write_text(_json.dumps(st, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _on_success(self, result: dict):''')
src = src.replace(
    "        self.login_success.emit(user, token)",
    '''        try:
            from app_logging import log as _log
            _log.info("Успешный вход: %s", user.get("username", "?"))
        except Exception:
            pass
        self._save_credentials()
        self.login_success.emit(user, token)''')
io.open(p, "w", encoding="utf-8").write(src)
print("login_window PATCHED")
