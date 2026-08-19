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
    if row:
        client_id = str(row[0])
        print(f"Client ID from DB: {client_id}")
    else:
        print("❌ Нет клиентов в БД")
        exit(1)

# Создаём услугу
service_resp = requests.post(f"{BASE}/services", headers=headers, json={
    "name": "Тестовая услуга E19.10",
    "category": "PERSONAL_TRAINER",
    "price": 1000.0,
    "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "is_active": True
})
print(f"Create Service Status: {service_resp.status_code}")
if service_resp.status_code != 201:
    print(f"❌ Не удалось создать услугу: {service_resp.text[:300]}")
    exit(1)

service = service_resp.json()
service_id = service["id"]
print(f"Service ID: {service_id}")

# Создаём бронирование через /services/{service_id}/book
booking_data = {
    "client_id": client_id,
    "service_id": service_id,  # <-- ДОБАВЛЯЕМ service_id в тело
    "booking_date": "2026-08-20T15:00:00"
}
booking_resp = requests.post(f"{BASE}/services/{service_id}/book", headers=headers, json=booking_data)
print(f"Create Booking Status: {booking_resp.status_code}")
print(f"Create Booking Response: {booking_resp.text[:300]}")

# Проверяем расписание
schedule_resp = requests.get(f"{BASE}/services/trainer-schedule?trainer_id=7db07a4c-0bf9-4a57-bd9f-9f088ba15783&date=2026-08-20", headers=headers)
print(f"Schedule Status: {schedule_resp.status_code}")
if schedule_resp.status_code == 200:
    schedule = schedule_resp.json()
    print(f"Schedule items: {len(schedule)}")
    found = any(b["service_id"] == service_id for b in schedule)
    print(f"Booking found in schedule: {found}")
