# tests/manual/test_e18_5.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем топ клиентов
resp = requests.get("http://localhost:8001/api/v1/analytics/top-clients?limit=10", headers=headers)
print(f"E18.5 Status: {resp.status_code}")
print(f"E18.5 Response: {resp.text[:500]}")
