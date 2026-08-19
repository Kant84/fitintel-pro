# tests/manual/close_shift.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Закрываем смену
close_data = {
    "session_id": "e4f34c47-b5fc-449f-be0a-c69252f4ab6e",
    "actual_cash": 0.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/close", headers=headers, json=close_data)
print(f"Close Status: {resp.status_code}")
print(f"Close Response: {resp.text[:500]}")
