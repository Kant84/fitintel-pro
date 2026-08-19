# tests/manual/test_e19_5.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Обновляем услугу
resp = requests.get("http://localhost:8001/api/v1/services", headers=headers)
services = resp.json()
if services:
    service_id = services[0]["id"]
    update = {"price": 750.00}
    resp = requests.put(f"http://localhost:8001/api/v1/services/{service_id}", headers=headers, json=update)
    print(f"E19.5 Status: {resp.status_code}")
    print(f"E19.5 Response: {resp.text[:500]}")
else:
    print("No services found")
