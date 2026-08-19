# tests/manual/test_e18_10.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем загрузку зон
resp = requests.get("http://localhost:8001/api/v1/analytics/zone-occupancy", headers=headers)
print(f"E18.10 Status: {resp.status_code}")
print(f"E18.10 Response: {resp.text[:500]}")
