# tests/manual/test_e15_13_fix.py
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

# Закрываем смену
close_data = {
    "session_id": session_id,
    "actual_cash": 0.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/close", headers=headers, json=close_data)
print(f"Close Status: {resp.status_code}")

# Теперь открываем смену для testuser123
shift = {
    "user_id": "03c4751d-2483-49fa-a4ca-9e2d8c266748",
    "starting_amount": 1000.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/open", headers=headers, json=shift)
print(f"E15.13 Status: {resp.status_code}")
print(f"E15.13 Response: {resp.text[:500]}")
