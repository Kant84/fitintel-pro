# tests/manual/test_e13_9.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

payment = {
    "amount": 1000,
    "payment_method": "CASH",
    "description": "Тест без client_id"
}
resp = requests.post("http://localhost:8001/api/v1/payments", headers=headers, json=payment)
print(f"E13.9 Status: {resp.status_code}")
print(f"E13.9 Response: {resp.text[:500]}")
