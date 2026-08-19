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
    "name": "Тестовая услуга E19.12",
    "category": "PERSONAL_TRAINER",
    "price": 1000.0,
    "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "is_active": True
})
service = service_resp.json()
service_id = service["id"]
print(f"Service ID: {service_id}")

# Создаём бронирование
booking_resp = requests.post(f"{BASE}/services/{service_id}/book", headers=headers, json={
    "client_id": client_id,
    "service_id": service_id,
    "booking_date": "2026-08-22T15:00:00"
})
booking = booking_resp.json()
booking_id = booking["id"]
print(f"Booking ID: {booking_id}")
print(f"Booking Status: {booking['status']}")

# Отменяем бронирование
cancel_resp = requests.post(f"{BASE}/services/bookings/{booking_id}/cancel", headers=headers)
print(f"Cancel Status: {cancel_resp.status_code}")
if cancel_resp.status_code == 200:
    cancelled = cancel_resp.json()
    print(f"New Status: {cancelled['status']}")

# Проверяем, что бронирование исчезло из расписания
schedule_resp = requests.get(f"{BASE}/services/trainer-schedule?trainer_id=7db07a4c-0bf9-4a57-bd9f-9f088ba15783&date=2026-08-22", headers=headers)
schedule = schedule_resp.json()
found = any(b["id"] == booking_id for b in schedule)
print(f"Booking in schedule after cancel: {found}")
