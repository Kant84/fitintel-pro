# tests/manual/test_e15_12.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем список смен
sessions = requests.get("http://localhost:8001/api/v1/cash-desk/sessions", headers=headers)
session_id = sessions.json()["items"][0]["id"]

# Печать отчёта (POST /print — если есть, или используем /report)
resp = requests.post(f"http://localhost:8001/api/v1/cash-desk/sessions/{session_id}/print", headers=headers)
print(f"E15.12 Status: {resp.status_code}")
print(f"E15.12 Response: {resp.text[:500]}")
