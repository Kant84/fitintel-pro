# tests/manual/test_e18_4.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем выручку по категориям
resp = requests.get("http://localhost:8001/api/v1/analytics/revenue?date=2026-06-27&group_by=category", headers=headers)
print(f"E18.4 Status: {resp.status_code}")
print(f"E18.4 Response: {resp.text[:500]}")
