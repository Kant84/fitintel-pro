# tests/manual/test_e16_4.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем список продаж
resp = requests.get("http://localhost:8001/api/v1/sales", headers=headers)
print(f"E16.4 Status: {resp.status_code}")
print(f"E16.4 Response: {resp.text[:500]}")
