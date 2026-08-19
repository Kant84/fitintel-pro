# test_e12_6_v2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём новый алерт
alert = {
    "camera_id": "hik_cam_02",
    "alert_type": "CUSTOM",
    "snapshot": "base64_snapshot_data_here",
    "confidence": 0.95,
    "zone": "main_entrance"
}
create_resp = requests.post("http://localhost:8001/api/v1/video-alerts", headers=headers, json=alert)
new_alert = create_resp.json()
alert_id = new_alert["id"]
print(f"Created alert: {alert_id}")

# Разрешаем первый раз
review = {
    "is_false_positive": False,
    "reviewed_by": 1
}
resp1 = requests.post(f"http://localhost:8001/api/v1/video-alerts/{alert_id}/review", headers=headers, json=review)
print(f"First review status: {resp1.status_code}")

# Пытаемся разрешить второй раз
resp2 = requests.post(f"http://localhost:8001/api/v1/video-alerts/{alert_id}/review", headers=headers, json=review)
print(f"E12.6 Second review status: {resp2.status_code}")
print(f"E12.6 Response: {resp2.text[:500]}")
