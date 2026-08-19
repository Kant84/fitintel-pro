# tests/manual/test_e13_11.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

payment = {
    "client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
    "amount": -100,
    "payment_method": "CASH",
    "description": "Тест с отрицательной суммой"
}
resp = requests.post("http://localhost:8001/api/v1/payments", headers=headers, json=payment)
print(f"E13.11 Status: {resp.status_code}")
print(f"E13.11 Response: {resp.text[:500]}")
