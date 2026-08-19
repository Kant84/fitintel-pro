# tests/manual/get_current_shift.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.get("http://localhost:8001/api/v1/cash-desk/current", headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
