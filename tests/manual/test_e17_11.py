# tests/manual/test_e17_11.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Обновляем прошивку
resp = requests.get("http://localhost:8001/api/v1/devices", headers=headers)
devices = resp.json().get("items", [])
if devices:
    device_id = devices[0]["id"]
    resp = requests.post(f"http://localhost:8001/api/v1/devices/{device_id}/firmware-update", headers=headers, json={"url": "http://example.com/firmware.bin"})
    print(f"E17.11 Status: {resp.status_code}")
    print(f"E17.11 Response: {resp.text[:500]}")
else:
    print("No devices found")
