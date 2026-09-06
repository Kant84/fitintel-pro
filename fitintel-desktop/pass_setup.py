"""pass_setup.py — автопрохождение мастера установки"""
import requests, json
from pathlib import Path

cfg = json.load(open("client_settings.json", encoding="utf-8"))
token = cfg.get("token", "")
base = cfg.get("api_base", "http://localhost:8001/api/v1")
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def post(path, data):
    try:
        r = requests.post(base + path, headers=h, json=data, timeout=10)
        print(f"  {path}: {r.status_code} — {r.text[:120]}")
        return r.status_code
    except Exception as e:
        print(f"  {path}: ERROR — {e}")
        return 0

print("=== Прохождение мастера ===\n")

# 1. Лицензия (ключ из вашего .env)
post("/setup/license/activate", {
    "license_key": "1fcb8631cfd7b2a2a32ab093643b4c12be43fb4219b0daaf49e59787a2551e51"
})

# 2. Админ (подтверждаем, что админ уже есть)
post("/setup/admin", {"confirmed": True})

# 3. Клуб (пробуем разные endpoint'ы)
club = {"name": "FitIntel Pro Club", "address": "Москва", "phone": "+7(926)362-76-32", "email": "sanichxxxx@mail.ru"}
for p in ["/setup/club-profile", "/setup/club", "/club-profile"]:
    if post(p, club) in (200, 201):
        break

# 4. Устройства — пропускаем
post("/setup/devices", {"skip": True})

# 5. Тарифы — пропускаем  
post("/setup/tariffs", {"skip": True})

# 6. Завершение
post("/setup/complete", {})

# Проверка
print("\n=== Проверка ===")
r = requests.get(base + "/setup/status", headers=h, timeout=10)
print(r.json())