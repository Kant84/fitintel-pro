# tests/manual/test_e15_13_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Пытаемся открыть смену другим кассиром
shift = {
    "user_id": "03c4751d-2483-49fa-a4ca-9e2d8c266748",
    "starting_amount": 1000.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/open", headers=headers, json=shift)
print(f"E15.13 Status: {resp.status_code}")
print(f"E15.13 Full Response:\n{resp.text}")
