import requests

BASE = "http://localhost:8001/api/v1"

# Авторизация
login = requests.post(f"{BASE}/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("✅ Авторизованы")

# Получаем клиента из БД
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id FROM clients LIMIT 1"))
    row = result.fetchone()
    client_id = str(row[0])
    print(f"Client ID: {client_id}")

# Создаём услугу
service_resp = requests.post(f"{BASE}/services", headers=headers, json={
    "name": "Тестовая услуга E19.11",
    "category": "PERSONAL_TRAINER",
    "price": 1000.0,
    "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "is_active": True,
    "max_capacity": 1
})
service = service_resp.json()
service_id = service["id"]
print(f"Service ID: {service_id}")

# Первое бронирование
booking1 = requests.post(f"{BASE}/services/{service_id}/book", headers=headers, json={
    "client_id": client_id,
    "service_id": service_id,
    "booking_date": "2026-08-21T15:00:00"
})
print(f"Booking 1 Status: {booking1.status_code}")

# Второе бронирование (конфликт)
booking2 = requests.post(f"{BASE}/services/{service_id}/book", headers=headers, json={
    "client_id": client_id,
    "service_id": service_id,
    "booking_date": "2026-08-21T15:00:00"
})
print(f"Booking 2 Status: {booking2.status_code}")
print(f"Booking 2 Response: {booking2.text[:200]}")
