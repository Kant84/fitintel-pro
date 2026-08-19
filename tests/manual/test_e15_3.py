# tests/manual/test_e15_3.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Закрываем смену
close_data = {
    "session_id": "b6fd03f6-386f-4d83-ad3d-0dedab1b6245",
    "actual_cash": 1000.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/close", headers=headers, json=close_data)
print(f"E15.3 Status: {resp.status_code}")
print(f"E15.3 Response: {resp.text[:500]}")
