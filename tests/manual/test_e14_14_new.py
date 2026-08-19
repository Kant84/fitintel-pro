# tests/manual/test_e14_14_new.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

url = "http://localhost:8001/api/v1/receipts/export?date_from=2026-06-01&date_to=2026-06-30&format=xlsx"
print(f"URL: {url}")
resp = requests.get(url, headers=headers)
print(f"E14.14 Status: {resp.status_code}")
print(f"E14.14 Response: {resp.text[:500]}")
