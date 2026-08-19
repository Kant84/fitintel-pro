# tests/manual/test_e13_13.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём платёж
payment = {
    "client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
    "amount": 100,
    "payment_method": "CASH",
    "description": "Тест для повторного возврата"
}
create_resp = requests.post("http://localhost:8001/api/v1/payments", headers=headers, json=payment)
payment_id = create_resp.json()["id"]

# Завершаем
requests.post(f"http://localhost:8001/api/v1/payments/{payment_id}/complete", headers=headers)

# Первый возврат
refund = {"amount": 50, "reason": "Первый возврат"}
resp1 = requests.post(f"http://localhost:8001/api/v1/payments/{payment_id}/refund", headers=headers, json=refund)
print(f"First refund: {resp1.status_code}")

# Второй возврат (должен быть отклонён)
refund2 = {"amount": 50, "reason": "Второй возврат"}
resp2 = requests.post(f"http://localhost:8001/api/v1/payments/{payment_id}/refund", headers=headers, json=refund2)
print(f"E13.13 Status: {resp2.status_code}")
print(f"E13.13 Response: {resp2.text[:500]}")
