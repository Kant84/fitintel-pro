# test_e12_full2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

alert = {
    "camera_id": "hik_cam_02",
    "alert_type": "CUSTOM",
    "snapshot": "base64_snapshot_data_here",
    "confidence": 0.95,
    "zone": "main_entrance"
}

resp = requests.post("http://localhost:8001/api/v1/video-alerts", headers=headers, json=alert)
print(f"Status: {resp.status_code}")
print(f"Full response:\n{resp.text}")
