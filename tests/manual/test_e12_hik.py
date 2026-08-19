# test_e12_hik.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# E12.1: Создание алерта с IP-камерой
alert = {
    "camera_id": "hik_cam_02",
    "alert_type": "CUSTOM",
    "snapshot": "base64_snapshot_data_here",
    "confidence": 0.95,
    "zone": "main_entrance"
}

resp = requests.post("http://localhost:8001/api/v1/video-alerts", headers=headers, json=alert)
print(f"E12.1 Status: {resp.status_code}")
print(f"E12.1 Response: {resp.text[:1000]}")
