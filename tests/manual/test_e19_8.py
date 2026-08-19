# tests/manual/test_e19_8.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Фильтруем по категории SAUNA
resp = requests.get("http://localhost:8001/api/v1/services?category=SAUNA", headers=headers)
print(f"E19.8 Status: {resp.status_code}")
print(f"E19.8 Response: {resp.text[:500]}")
