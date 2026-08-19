# tests/manual/test_e18_8.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем отток
resp = requests.get("http://localhost:8001/api/v1/analytics/churn?days=30", headers=headers)
print(f"E18.8 Status: {resp.status_code}")
print(f"E18.8 Response: {resp.text[:500]}")
