# tests/manual/test_e17_13.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Фильтруем по статусу offline
resp = requests.get("http://localhost:8001/api/v1/devices?status=offline", headers=headers)
print(f"E17.13 Status: {resp.status_code}")
print(f"E17.13 Response: {resp.text[:500]}")
