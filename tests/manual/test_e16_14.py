# tests/manual/test_e16_14.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Отчёт по продажам за день
resp = requests.get("http://localhost:8001/api/v1/sales/report?date=2026-06-27", headers=headers)
print(f"E16.14 Status: {resp.status_code}")
print(f"E16.14 Response: {resp.text[:500]}")
