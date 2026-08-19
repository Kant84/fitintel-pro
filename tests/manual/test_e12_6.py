# test_e12_6.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем список и берём первый ID (уже разрешённый)
list_resp = requests.get("http://localhost:8001/api/v1/video-alerts", headers=headers)
alerts = list_resp.json()
alert_id = alerts[0]["id"]

# Пытаемся разрешить уже разрешённый
review = {
    "is_false_positive": False,
    "reviewed_by": 1
}

resp = requests.post(f"http://localhost:8001/api/v1/video-alerts/{alert_id}/review", headers=headers, json=review)
print(f"E12.6 Status: {resp.status_code}")
print(f"E12.6 Response: {resp.text[:500]}")
