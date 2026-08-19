# tests/manual/test_e13_7.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

online_payment = {
    "client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
    "amount": 2000,
    "payment_method": "CARD",
    "payment_system": "SBP",
    "description": "Тестовая онлайн-оплата"
}
resp = requests.post("http://localhost:8001/api/v1/payments/online", headers=headers, json=online_payment)
print(f"E13.7 Status: {resp.status_code}")
print(f"E13.7 Response: {resp.text[:500]}")
