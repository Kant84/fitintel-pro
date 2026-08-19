# test_e12_11.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем snapshot с камеры
resp = requests.get("http://localhost:8001/api/v1/devices/hik_cam_02/snapshot", headers=headers)
print(f"E12.11 Status: {resp.status_code}")
print(f"E12.11 Response: {resp.text[:500]}")
