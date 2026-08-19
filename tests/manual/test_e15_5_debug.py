# tests/manual/test_e15_5_debug.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Открываем смену
shift = {
    "user_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "starting_amount": 1000.00
}
open_resp = requests.post("http://localhost:8001/api/v1/cash-desk/open", headers=headers, json=shift)
print(f"Open Status: {open_resp.status_code}")
print(f"Open Response: {open_resp.text[:500]}")

# Если уже открыта — получаем текущую смену
if open_resp.status_code == 409:
    current = requests.get("http://localhost:8001/api/v1/cash-desk/current", headers=headers)
    print(f"Current Status: {current.status_code}")
    print(f"Current Response: {current.text[:500]}")
    session_id = current.json()["session"]["id"]
else:
    session_id = open_resp.json()["id"]

print(f"Session ID: {session_id}")

# Вносим наличные
deposit = {
    "session_id": session_id,
    "amount": 500.00,
    "type": "DEPOSIT",
    "reason": "Внесение наличных"
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/operation", headers=headers, json=deposit)
print(f"E15.5 Status: {resp.status_code}")
print(f"E15.5 Response: {resp.text[:500]}")
