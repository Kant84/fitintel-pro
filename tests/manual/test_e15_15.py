# tests/manual/test_e15_15.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем текущую смену
current = requests.get("http://localhost:8001/api/v1/cash-desk/current", headers=headers)
if current.json().get("has_open_session"):
    session_id = current.json()["session"]["id"]
    # Z-отчёт через ФР
    resp = requests.post(f"http://localhost:8001/api/v1/cash-desk/sessions/{session_id}/z-report?fr=atol", headers=headers)
    print(f"E15.15 Status: {resp.status_code}")
    print(f"E15.15 Response: {resp.text[:500]}")
else:
    print("E15.15: Нет открытой смены")
