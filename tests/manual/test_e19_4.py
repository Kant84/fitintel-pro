# tests/manual/test_e19_4.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем услугу по ID
resp = requests.get("http://localhost:8001/api/v1/services", headers=headers)
services = resp.json()
if services:
    service_id = services[0]["id"]
    resp = requests.get(f"http://localhost:8001/api/v1/services/{service_id}", headers=headers)
    print(f"E19.4 Status: {resp.status_code}")
    print(f"E19.4 Response: {resp.text[:500]}")
else:
    print("No services found")
