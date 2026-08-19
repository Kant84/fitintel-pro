# tests/manual/test_e17_4.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем устройство по ID
device_id = "a1effed6-357f-49fd-97b0-0e85ed1db91a"
resp = requests.get(f"http://localhost:8001/api/v1/devices/{device_id}", headers=headers)
print(f"E17.4 Status: {resp.status_code}")
print(f"E17.4 Response: {resp.text[:500]}")
