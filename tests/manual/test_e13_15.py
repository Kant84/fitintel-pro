# tests/manual/test_e13_15.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Фильтрация по статусу COMPLETED
resp = requests.get("http://localhost:8001/api/v1/payments/me?status=COMPLETED", headers=headers)
print(f"E13.15 Status: {resp.status_code}")
print(f"E13.15 Response: {resp.text[:500]}")
