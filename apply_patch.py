FILE = "fitintel-desktop/windows/clients_tab.py"

with open(FILE, "r", encoding="utf-8") as f:
    txt = f.read()

# 1. Фильтр is_active в _on_loaded
old = """    def _on_loaded(self, clients: list):
        self._all_data = clients
        self._render(clients)"""

new = """    def _on_loaded(self, clients: list):
        # Фильтруем: показываем только активных клиентов
        self._all_data = [c for c in clients if c.get("is_active", True)]
        self._render(self._all_data)"""

if old in txt:
    txt = txt.replace(old, new)
    print("✅ _on_loaded: фильтр is_active добавлен")
else:
    print("⚠️ _on_loaded не найден")

# 2. Замена delete_client на update_client
old2 = "self.api.delete_client(str(c[\"id\"]))"
new2 = "self.api.update_client(str(c[\"id\"]), {\"is_active\": False, \"status\": \"INACTIVE\"})"

if old2 in txt:
    txt = txt.replace(old2, new2)
    print("✅ delete_client заменён на update_client")
else:
    print("⚠️ delete_client не найден")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(txt)

print("Done!")