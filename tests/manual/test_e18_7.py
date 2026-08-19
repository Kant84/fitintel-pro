# tests/manual/test_e18_7.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем конверсию
resp = requests.get("http://localhost:8001/api/v1/analytics/conversion", headers=headers)
print(f"E18.7 Status: {resp.status_code}")
print(f"E18.7 Response: {resp.text[:500]}")
