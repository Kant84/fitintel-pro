# tests/manual/test_e17_10.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Перезагружаем устройство
resp = requests.get("http://localhost:8001/api/v1/devices", headers=headers)
devices = resp.json().get("items", [])
if devices:
    device_id = devices[0]["id"]
    resp = requests.post(f"http://localhost:8001/api/v1/devices/{device_id}/reboot", headers=headers)
    print(f"E17.10 Status: {resp.status_code}")
    print(f"E17.10 Response: {resp.text[:500]}")
else:
    print("No devices found")
