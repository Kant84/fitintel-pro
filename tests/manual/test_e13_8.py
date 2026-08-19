# tests/manual/test_e13_8.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

webhook_data = {
    "payment_id": "999c83f5-75d5-40af-ad67-b86f77d0f83d",
    "event": "payment.succeeded",
    "object": {
        "id": "test-payment-id",
        "status": "succeeded",
        "amount": {"value": "1000.00", "currency": "RUB"}
    }
}
resp = requests.post("http://localhost:8001/api/v1/payments/webhook/sbp", headers=headers, json=webhook_data)
print(f"E13.8 Status: {resp.status_code}")
print(f"E13.8 Response: {resp.text[:500]}")
