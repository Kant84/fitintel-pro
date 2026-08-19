# tests/manual/test_e14_9_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

subscription_id = "eab8e16b-8d7b-4c02-80f3-f961f3e426a1"
extend = {
    "days": 30,
    "reason": "Попытка продлить отменённую"
}
resp = requests.post(f"http://localhost:8001/api/v1/subscriptions/{subscription_id}/extend", headers=headers, json=extend)
print(f"E14.9 Status: {resp.status_code}")
print(f"E14.9 Full Response:\n{resp.text}")
