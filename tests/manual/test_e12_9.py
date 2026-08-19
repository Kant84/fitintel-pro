# test_e12_9.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Фильтрация по camera_id
resp = requests.get("http://localhost:8001/api/v1/video-alerts?camera_id=hik_cam_02", headers=headers)
print(f"E12.9 Status: {resp.status_code}")
print(f"E12.9 Response: {resp.text[:500]}")
