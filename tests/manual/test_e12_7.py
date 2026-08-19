# test_e12_7.py
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

resp = requests.delete(f"http://localhost:8001/api/v1/video-alerts/{alert_id}", headers=headers)
print(f"E12.7 Status: {resp.status_code}")
print(f"E12.7 Response: {resp.text[:500]}")
