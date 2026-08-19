# test_e12_5_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем список и берём первый ID
list_resp = requests.get("http://localhost:8001/api/v1/video-alerts", headers=headers)
alerts = list_resp.json()
alert_id = alerts[0]["id"]

# Разрешаем алерт
review = {
    "is_false_positive": False,
    "reviewed_by": 1  # ID пользователя
}

resp = requests.post(f"http://localhost:8001/api/v1/video-alerts/{alert_id}/review", headers=headers, json=review)
print(f"E12.5 Status: {resp.status_code}")
print(f"E12.5 Full Response:\n{resp.text}")
