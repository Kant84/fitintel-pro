# test_e12_10.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Очистка старых алертов (старше 30 дней)
resp = requests.post("http://localhost:8001/api/v1/video-alerts/archive/cleanup", headers=headers)
print(f"E12.10 Status: {resp.status_code}")
print(f"E12.10 Response: {resp.text[:500]}")
