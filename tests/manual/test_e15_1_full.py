# tests/manual/test_e15_1_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

shift = {
    "user_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "starting_amount": 1000.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/open", headers=headers, json=shift)
print(f"E15.1 Status: {resp.status_code}")
print(f"E15.1 Full Response:\n{resp.text}")
