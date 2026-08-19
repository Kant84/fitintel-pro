# tests/manual/test_e14_15.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

receipt_id = "5f1afc0a-30f0-4a47-ad97-8e7654eeb7f8"
resp = requests.post(f"http://localhost:8001/api/v1/receipts/{receipt_id}/fiscalize?driver=atol", headers=headers)
print(f"E14.15 Status: {resp.status_code}")
print(f"E14.15 Response: {resp.text[:500]}")
