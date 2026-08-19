# tests/manual/test_e16_8.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём продажу со скидкой
sale = {
    "items": [
        {"product_id": "11111111-1111-1111-1111-111111111111", "quantity": 2, "price": 100.00}
    ],
    "payment_method": "CASH",
    "discount_code": "DISCOUNT10"
}
resp = requests.post("http://localhost:8001/api/v1/sales", headers=headers, json=sale)
print(f"E16.8 Status: {resp.status_code}")
print(f"E16.8 Response: {resp.text[:500]}")
