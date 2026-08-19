# tests/manual/test_e17_1.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Регистрируем устройство с уникальным кодом
import uuid
device = {
    "name": "Тестовый турникет",
    "type": "turnstile",
    "ip_address": "192.168.1.100",
    "code": f"TURNSTILE-{uuid.uuid4().hex[:8].upper()}"
}
resp = requests.post("http://localhost:8001/api/v1/devices", headers=headers, json=device)
print(f"E17.1 Status: {resp.status_code}")
print(f"E17.1 Response: {resp.text[:500]}")
