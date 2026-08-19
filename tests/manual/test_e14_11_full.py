# tests/manual/test_e14_11_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

refund_receipt = {
    "payment_id": "df254135-7e3a-46d5-98bd-45011e0b7bce",
    "receipt_type": "REFUND",
    "original_receipt_id": "5f1afc0a-30f0-4a47-ad97-8e7654eeb7f8",
    "items": [
        {
            "name": "Возврат абонемента",
            "quantity": 1,
            "price": -1000.00,
            "total": -1000.00
        }
    ]
}
resp = requests.post("http://localhost:8001/api/v1/receipts", headers=headers, json=refund_receipt)
print(f"E14.11 Status: {resp.status_code}")
print(f"E14.11 Full Response:\n{resp.text}")
