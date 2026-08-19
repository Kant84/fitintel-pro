# tests/manual/test_e13_12.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём новый платёж
payment = {
    "client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
    "amount": 100,
    "payment_method": "CASH",
    "description": "Тест для возврата"
}
create_resp = requests.post("http://localhost:8001/api/v1/payments", headers=headers, json=payment)
payment_id = create_resp.json()["id"]

# Завершаем платёж
requests.post(f"http://localhost:8001/api/v1/payments/{payment_id}/complete", headers=headers)

# Пытаемся вернуть больше суммы
refund = {
    "amount": 200,
    "reason": "Попытка вернуть больше суммы"
}
resp = requests.post(f"http://localhost:8001/api/v1/payments/{payment_id}/refund", headers=headers, json=refund)
print(f"E13.12 Status: {resp.status_code}")
print(f"E13.12 Response: {resp.text[:500]}")
