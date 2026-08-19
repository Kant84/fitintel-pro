# tests/manual/test_e15_6.py
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

# Изъятие наличных
withdraw = {
    "session_id": session_id,
    "amount": 200.00,
    "operation_type": "WITHDRAWAL",
    "payment_method": "CASH",
    "reason": "Изъятие наличных"
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/operation", headers=headers, json=withdraw)
print(f"E15.6 Status: {resp.status_code}")
print(f"E15.6 Response: {resp.text[:500]}")
