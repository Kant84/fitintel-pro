# tests/manual/test_e15_5.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем текущую смену
current = requests.get("http://localhost:8001/api/v1/cash-desk/current", headers=headers)
session_id = current.json()["session"]["id"]
print(f"Session ID: {session_id}")

# Вносим наличные
deposit = {
    "session_id": session_id,
    "amount": 500.00,
    "operation_type": "DEPOSIT",
    "payment_method": "CASH",
    "reason": "Внесение наличных"
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/operation", headers=headers, json=deposit)
print(f"E15.5 Status: {resp.status_code}")
print(f"E15.5 Response: {resp.text[:500]}")
