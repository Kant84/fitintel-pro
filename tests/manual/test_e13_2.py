# tests/manual/test_e13_2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.get("http://localhost:8001/api/v1/payments/me", headers=headers)
print(f"E13.2 Status: {resp.status_code}")
print(f"E13.2 Response: {resp.text[:500]}")
