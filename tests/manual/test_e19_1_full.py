# tests/manual/test_e19_1_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

service = {
    "name": "Тестовая услуга",
    "category": "SAUNA",
    "price": 500.00,
    "duration": 60
}
resp = requests.post("http://localhost:8001/api/v1/services", headers=headers, json=service)
print(f"E19.1 Status: {resp.status_code}")
print(f"E19.1 Full Response:\n{resp.text}")
