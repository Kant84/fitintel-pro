# test_e12_12.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Пытаемся получить snapshot с несуществующей камеры
resp = requests.get("http://localhost:8001/api/v1/devices/offline_cam/snapshot", headers=headers)
print(f"E12.12 Status: {resp.status_code}")
print(f"E12.12 Response: {resp.text[:500]}")
