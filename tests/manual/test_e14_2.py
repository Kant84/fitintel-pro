# tests/manual/test_e14_2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

receipt = {
    "items": [
        {
            "name": "Тест без payment_id",
            "quantity": 1,
            "price": 100.00,
            "total": 100.00
        }
    ]
}
resp = requests.post("http://localhost:8001/api/v1/receipts", headers=headers, json=receipt)
print(f"E14.2 Status: {resp.status_code}")
print(f"E14.2 Response: {resp.text[:500]}")
