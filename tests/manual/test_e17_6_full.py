# tests/manual/test_e17_6_full.py
import requests
import random
import uuid

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

device = {
    "name": "Устройство для удаления",
    "type": "turnstile",
    "ip_address": f"192.168.1.{random.randint(201, 250)}",
    "code": f"DELETE-{uuid.uuid4().hex[:8].upper()}"
}
create_resp = requests.post("http://localhost:8001/api/v1/devices", headers=headers, json=device)
device_id = create_resp.json()["id"]

resp = requests.delete(f"http://localhost:8001/api/v1/devices/{device_id}", headers=headers)
print(f"E17.6 Status: {resp.status_code}")
print(f"E17.6 Full Response:\n{resp.text}")
