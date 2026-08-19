import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
BASE = "http://localhost:8001/api/v1"

# Авторизация
login = requests.post(f"{BASE}/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("✅ Авторизованы")

# 1. Клиент из БД
with engine.connect() as conn:
    client_id = str(conn.execute(text("SELECT id FROM clients LIMIT 1")).fetchone()[0])
print(f"Client ID: {client_id}")

# 2. Чистим ВСЕ бронирования клиента (чтобы не было 409)
with engine.connect() as conn:
    with conn.begin():
        res = conn.execute(
            text("DELETE FROM service_bookings WHERE client_id = :cid"),
            {"cid": client_id}
        )
print(f"🧹 Удалено старых бронирований: {res.rowcount}")

# 3. Новая услуга
service_resp = requests.post(f"{BASE}/services", headers=headers, json={
    "name": "Тестовая услуга E19.15",
    "category": "PERSONAL_TRAINER",
    "price": 1000.0,
    "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "is_active": True
})
if service_resp.status_code != 201:
    print(f"❌ Услуга не создана: {service_resp.text[:200]}")
    exit(1)
service_id = service_resp.json()["id"]
print(f"Service ID: {service_id}")

# 4. Бронирование послезавтра на 23:00
booking_time = f"{(datetime.now() + timedelta(days=2)).date()}T23:00:00"
booking_resp = requests.post(
    f"{BASE}/services/{service_id}/book",
    headers=headers,
    json={"client_id": client_id, "service_id": service_id, "booking_date": booking_time}
)
print(f"Booking Status: {booking_resp.status_code}")
if booking_resp.status_code != 201:
    print(f"❌ Бронирование не создано: {booking_resp.text[:200]}")
    exit(1)
booking_id = booking_resp.json()["id"]
print(f"Booking ID: {booking_id}")

# 5. Отправка напоминания — то, что проверяет E19.15
reminder_resp = requests.post(
    f"{BASE}/services/bookings/{booking_id}/send-reminder",
    headers=headers
)
print(f"Reminder Status: {reminder_resp.status_code}")
print(f"Reminder Response: {reminder_resp.text[:300]}")

if reminder_resp.status_code == 200:
    print("✅ E19.15 ПРОЙДЕН — напоминание отправлено")
elif reminder_resp.status_code == 404:
    print("⚠️ E19.15: эндпоинт send-reminder не существует — фича не реализована")
else:
    print(f"⚠️ E19.15: напоминание вернуло {reminder_resp.status_code} — смотрим тело ответа")
