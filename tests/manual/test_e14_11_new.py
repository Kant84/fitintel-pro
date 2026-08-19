# tests/manual/test_e14_11_new.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём возвратный чек с новым payment_id
refund_receipt = {
    "payment_id": "65af403b-69a7-4558-a309-c95a4210d521",
    "receipt_type": "REFUND",
    "original_receipt_id": "5f1afc0a-30f0-4a47-ad97-8e7654eeb7f8",
    "items": [
        {
            "name": "Возврат абонемента",
            "quantity": 1,
            "price": -2500.00,
            "total": -2500.00
        }
    ]
}
resp = requests.post("http://localhost:8001/api/v1/receipts", headers=headers, json=refund_receipt)
print(f"E14.11 Status: {resp.status_code}")
print(f"E14.11 Response: {resp.text[:500]}")
