# tests/manual/test_e17_9.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Проверяем ping offline устройства
device_id = "23c515f2-dc36-41d7-a114-d3ca876f5639"
resp = requests.get(f"http://localhost:8001/api/v1/devices/{device_id}/ping", headers=headers)
print(f"E17.9 Status: {resp.status_code}")
print(f"E17.9 Response: {resp.text[:500]}")
