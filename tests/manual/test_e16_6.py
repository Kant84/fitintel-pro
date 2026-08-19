# tests/manual/test_e16_6.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Возврат продажи (менее 24 часов)
sale_id = "8a393df5-6287-4219-976f-225e3fd7c85b"
resp = requests.post(f"http://localhost:8001/api/v1/sales/{sale_id}/refund", headers=headers, json={"reason": "Возврат товара"})
print(f"E16.6 Status: {resp.status_code}")
print(f"E16.6 Response: {resp.text[:500]}")
