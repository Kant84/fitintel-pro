# tests/manual/test_e18_1_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.get("http://localhost:8001/api/v1/analytics/visits?date=2026-06-27", headers=headers)
print(f"E18.1 Status: {resp.status_code}")
print(f"E18.1 Full Response:\n{resp.text}")
