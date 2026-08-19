# tests/manual/test_e18_13.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Сравниваем периоды
resp = requests.get("http://localhost:8001/api/v1/analytics/compare?period1=2026-06-01&period2=2026-06-15", headers=headers)
print(f"E18.13 Status: {resp.status_code}")
print(f"E18.13 Response: {resp.text[:500]}")
