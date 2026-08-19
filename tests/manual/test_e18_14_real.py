# tests/manual/test_e18_14_real.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Прогноз на 7 дней (используем данные за 2026-06-27)
resp = requests.post("http://localhost:8001/api/v1/analytics/forecast", headers=headers, json={
    "metric": "attendance",
    "days_ahead": 7
})
print(f"E18.14 Status: {resp.status_code}")
print(f"E18.14 Response: {resp.text[:1000]}")
