# tests/manual/test_e15_13.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Пытаемся открыть смену другим кассиром (используем тот же user_id, но система должна отклонить)
shift = {
    "user_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "starting_amount": 1000.00
}
resp = requests.post("http://localhost:8001/api/v1/cash-desk/open", headers=headers, json=shift)
print(f"E15.13 Status: {resp.status_code}")
print(f"E15.13 Response: {resp.text[:500]}")
