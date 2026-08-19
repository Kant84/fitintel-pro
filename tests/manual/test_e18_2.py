# tests/manual/test_e18_2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем посещаемость за период
resp = requests.get("http://localhost:8001/api/v1/analytics/visits?date_from=2026-06-20&date_to=2026-06-27", headers=headers)
print(f"E18.2 Status: {resp.status_code}")
print(f"E18.2 Response: {resp.text[:500]}")
