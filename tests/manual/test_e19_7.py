# tests/manual/test_e19_7.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём услугу
service = {
    "name": "Услуга с бронированием",
    "category": "SAUNA",
    "price": 200.00
}
create_resp = requests.post("http://localhost:8001/api/v1/services", headers=headers, json=service)
service_id = create_resp.json()["id"]
print(f"Created service: {service_id}")

# Используем известного клиента
client_id = "473d5de8-3f46-4c95-9950-dd0c49c9a8d3"

# Создаём бронирование
booking = {
    "client_id": client_id,
    "service_id": service_id,
    "booking_date": "2026-06-30T10:00:00"
}
booking_resp = requests.post(f"http://localhost:8001/api/v1/services/{service_id}/book", headers=headers, json=booking)
print(f"Booking Status: {booking_resp.status_code}")
print(f"Booking Response: {booking_resp.text[:500]}")

# Пытаемся удалить услугу с бронированием
resp = requests.delete(f"http://localhost:8001/api/v1/services/{service_id}", headers=headers)
print(f"E19.7 Status: {resp.status_code}")
print(f"E19.7 Response: {resp.text[:500]}")
