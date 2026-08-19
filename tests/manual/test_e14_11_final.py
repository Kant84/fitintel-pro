# tests/manual/test_e14_11_final.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём возвратный чек с платежом без чека
refund_receipt = {
    "payment_id": "a5e13500-2af9-4f3c-be20-750dede06373",
    "receipt_type": "REFUND",
    "items": [{"name": "Возврат", "quantity": 1, "price": -100.00, "total": -100.00}]
}
resp = requests.post("http://localhost:8001/api/v1/receipts", headers=headers, json=refund_receipt)
print(f"E14.11 Status: {resp.status_code}")
print(f"E14.11 Response: {resp.text[:500]}")
