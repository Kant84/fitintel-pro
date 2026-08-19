# tests/manual/test_e16_2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Продажа без товаров
sale = {
    "items": [],
    "payment_method": "CASH"
}
resp = requests.post("http://localhost:8001/api/v1/sales", headers=headers, json=sale)
print(f"E16.2 Status: {resp.status_code}")
print(f"E16.2 Response: {resp.text[:500]}")
