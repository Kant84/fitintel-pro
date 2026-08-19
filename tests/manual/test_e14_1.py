# tests/manual/test_e14_1.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём чек
receipt = {
    "payment_id": "df254135-7e3a-46d5-98bd-45011e0b7bce",  # ID платежа из E13
    "items": [
        {
            "name": "Абонемент на 1 месяц",
            "quantity": 1,
            "price": 1000.00,
            "total": 1000.00
        }
    ]
}
resp = requests.post("http://localhost:8001/api/v1/receipts", headers=headers, json=receipt)
print(f"E14.1 Status: {resp.status_code}")
print(f"E14.1 Response: {resp.text[:500]}")
