import requests
from datetime import datetime, timedelta

BASE = "http://localhost:8001/api/v1"

# Авторизация
login = requests.post(f"{BASE}/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("✅ Авторизованы")

# Получаем клиента
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id FROM clients LIMIT 1"))
    client_id = str(result.fetchone()[0])
    print(f"Client ID: {client_id}")

# Создаём услугу
service_resp = requests.post(f"{BASE}/services", headers=headers, json={
    "name": "Тестовая услуга E19.13",
    "category": "PERSONAL_TRAINER",
    "price": 1000.0,
    "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "is_active": True
})
service = service_resp.json()
service_id = service["id"]
print(f"Service ID: {service_id}")

# Бронируем на время через 1 час (меньше 24ч)
booking_time = (datetime.now() + timedelta(hours=1)).isoformat()
booking_resp = requests.post(f"{BASE}/services/{service_id}/book", headers=headers, json={
    "client_id": client_id,
    "service_id": service_id,
    "booking_date": booking_time
})
booking = booking_resp.json()
booking_id = booking["id"]
print(f"Booking ID: {booking_id} (time: {booking_time})")

# Пытаемся отменить (<24ч)
cancel_resp = requests.post(f"{BASE}/services/bookings/{booking_id}/cancel", headers=headers)
print(f"Cancel Status: {cancel_resp.status_code}")
print(f"Cancel Response: {cancel_resp.text[:200]}")
