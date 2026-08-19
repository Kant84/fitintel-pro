# tests/manual/test_e13_14.py
import requests

payment = {
    "client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
    "amount": 100,
    "payment_method": "CASH",
    "description": "Тест без авторизации"
}
resp = requests.post("http://localhost:8001/api/v1/payments", json=payment)
print(f"E13.14 Status: {resp.status_code}")
print(f"E13.14 Response: {resp.text[:500]}")
