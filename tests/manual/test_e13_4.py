# tests/manual/test_e13_4.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

client_id = "473d5de8-3f46-4c95-9950-dd0c49c9a8d3"
resp = requests.get(f"http://localhost:8001/api/v1/payments/client/{client_id}", headers=headers)
print(f"E13.4 Status: {resp.status_code}")
print(f"E13.4 Response: {resp.text[:500]}")
