# tests/manual/test_device_types.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем все устройства
resp = requests.get("http://localhost:8001/api/v1/devices", headers=headers)
devices = resp.json().get("items", [])

print(f"Всего устройств: {len(devices)}")
print("\nПо типам:")
types = {}
for d in devices:
    t = d["device_type"]
    types[t] = types.get(t, 0) + 1

for t, count in types.items():
    print(f"  {t}: {count}")

# Тестируем команды для разных типов
print("\n--- Тестируем команды ---")
for device in devices:
    device_id = device["id"]
    device_type = device["device_type"]
    
    # Команда в зависимости от типа
    if device_type == "camera":
        command = {"protocol": "http_api", "command": "capture", "params": {"resolution": "1080p"}}
    elif device_type == "locker":
        command = {"protocol": "mqtt", "command": "unlock", "params": {"locker_id": 1}}
    elif device_type == "card_reader":
        command = {"protocol": "serial", "command": "read_card", "params": {"port": "COM2"}}
    elif device_type == "display":
        command = {"protocol": "websocket", "command": "show_text", "params": {"text": "Welcome!"}}
    elif device_type == "sensor":
        command = {"protocol": "modbus_tcp", "command": "read_temp", "params": {"register": 0, "count": 1}}
    else:
        command = {"protocol": "http_api", "command": "status", "params": {}}
    
    resp = requests.post(f"http://localhost:8001/api/v1/devices/{device_id}/protocol", headers=headers, json=command)
    print(f"{device_type}: {resp.status_code} - {resp.text[:100]}")
