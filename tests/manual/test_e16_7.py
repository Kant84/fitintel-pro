# tests/manual/test_e16_7.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Возврат продажи старше 24ч
sale_id = "22222222-2222-2222-2222-222222222222"
resp = requests.post(f"http://localhost:8001/api/v1/sales/{sale_id}/refund", headers=headers, json={"reason": "Возврат товара"})
print(f"E16.7 Status: {resp.status_code}")
print(f"E16.7 Response: {resp.text[:500]}")
