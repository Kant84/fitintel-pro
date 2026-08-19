# tests/manual/test_e13_6.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

payment_id = "df254135-7e3a-46d5-98bd-45011e0b7bce"
refund = {
    "amount": 500,
    "reason": "Тестовый возврат"
}
resp = requests.post(f"http://localhost:8001/api/v1/payments/{payment_id}/refund", headers=headers, json=refund)
print(f"E13.6 Status: {resp.status_code}")
print(f"E13.6 Response: {resp.text[:500]}")
