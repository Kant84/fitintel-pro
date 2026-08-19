# tests/manual/test_e17_2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Пытаемся зарегистрировать устройство с тем же IP, но новым кодом
import uuid
device = {
    "name": "Дублирующий турникет",
    "type": "turnstile",
    "ip_address": "192.168.1.100",
    "code": f"TURNSTILE-{uuid.uuid4().hex[:8].upper()}"
}
resp = requests.post("http://localhost:8001/api/v1/devices", headers=headers, json=device)
print(f"E17.2 Status: {resp.status_code}")
print(f"E17.2 Response: {resp.text[:500]}")
