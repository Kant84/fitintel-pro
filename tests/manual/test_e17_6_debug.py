# tests/manual/test_e17_6_debug.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

import uuid
device = {
    "name": "Устройство для удаления",
    "type": "turnstile",
    "ip_address": "192.168.1.200",
    "code": f"DELETE-{uuid.uuid4().hex[:8].upper()}"
}
create_resp = requests.post("http://localhost:8001/api/v1/devices", headers=headers, json=device)
print(f"Create Status: {create_resp.status_code}")
print(f"Create Response: {create_resp.text[:500]}")
