# tests/manual/test_e17_9_new.py
import requests
import random
import uuid

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём устройство без heartbeat
device = {
    "name": "Offline устройство",
    "type": "turnstile",
    "ip_address": f"192.168.1.{random.randint(254, 254)}",
    "code": f"OFFLINE-{uuid.uuid4().hex[:8].upper()}"
}
create_resp = requests.post("http://localhost:8001/api/v1/devices", headers=headers, json=device)
device_id = create_resp.json()["id"]

# Проверяем ping
resp = requests.post(f"http://localhost:8001/api/v1/devices/{device_id}/ping", headers=headers)
print(f"E17.9 Status: {resp.status_code}")
print(f"E17.9 Response: {resp.text[:500]}")
