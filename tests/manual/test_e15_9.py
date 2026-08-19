# tests/manual/test_e15_9.py
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

# Получаем операции смены
resp = requests.get(f"http://localhost:8001/api/v1/cash-desk/sessions/{session_id}/operations", headers=headers)
print(f"E15.9 Status: {resp.status_code}")
print(f"E15.9 Response: {resp.text[:500]}")
