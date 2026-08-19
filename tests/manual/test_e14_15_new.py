# tests/manual/test_e14_15_new.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Используем возвратный чек E14.11 (не фискализирован)
receipt_id = "1c4eae87-1e97-43b1-92d1-525ed8fc8d47"
resp = requests.post(f"http://localhost:8001/api/v1/receipts/{receipt_id}/fiscalize?driver=atol", headers=headers)
print(f"E14.15 Status: {resp.status_code}")
print(f"E14.15 Response: {resp.text[:500]}")
