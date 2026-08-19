# tests/manual/test_e14_4_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

client_id = "473d5de8-3f46-4c95-9950-dd0c49c9a8d3"
resp = requests.get(f"http://localhost:8001/api/v1/subscriptions/client/{client_id}", headers=headers)
print(f"E14.4 Status: {resp.status_code}")
print(f"E14.4 Full Response:\n{resp.text}")
