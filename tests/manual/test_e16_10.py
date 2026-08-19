# tests/manual/test_e16_10.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём продажу с оплатой наличными
sale = {
    "items": [
        {"product_id": "11111111-1111-1111-1111-111111111111", "quantity": 1, "price": 100.00}
    ],
    "payment_method": "CASH"
}
resp = requests.post("http://localhost:8001/api/v1/sales", headers=headers, json=sale)
print(f"E16.10 Status: {resp.status_code}")
print(f"E16.10 Response: {resp.text[:500]}")
