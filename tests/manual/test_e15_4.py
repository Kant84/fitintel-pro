# tests/manual/test_e15_4.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Открываем смену с starting_amount
shift = {
    "user_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "starting_amount": 5000.00
}
open_resp = requests.post("http://localhost:8001/api/v1/cash-desk/open", headers=headers, json=shift)
session_id = open_resp.json()["id"]
print(f"Opened session: {session_id}")

# Закрываем смену с другой суммой (расхождение)
close_data = {
    "session_id": session_id,
    "actual_cash": 4500.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/close", headers=headers, json=close_data)
print(f"E15.4 Status: {resp.status_code}")
print(f"E15.4 Response: {resp.text[:500]}")
