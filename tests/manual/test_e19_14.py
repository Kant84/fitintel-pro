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

# Создаём услугу с тренером
service_resp = requests.post(f"{BASE}/services", headers=headers, json={
    "name": "Тестовая услуга E19.14",
    "category": "PERSONAL_TRAINER",
    "price": 1000.0,
    "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
    "is_active": True
})
service = service_resp.json()
service_id = service["id"]
print(f"Service ID: {service_id}")

# Создаём бронирование на завтра (чтобы не было конфликтов)
tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
booking_time = f"{tomorrow}T15:00:00"
booking_resp = requests.post(f"{BASE}/services/{service_id}/book", headers=headers, json={
    "client_id": client_id,
    "service_id": service_id,
    "booking_date": booking_time
})
print(f"Booking Status: {booking_resp.status_code}")
if booking_resp.status_code == 201:
    print(f"Booking created: {booking_resp.json()['id']}")
else:
    print(f"Booking error: {booking_resp.text[:200]}")

# Получаем расписание тренера на завтра
schedule_resp = requests.get(
    f"{BASE}/services/trainer-schedule",
    headers=headers,
    params={
        "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783",
        "date": tomorrow
    }
)
print(f"Schedule Status: {schedule_resp.status_code}")
if schedule_resp.status_code == 200:
    schedule = schedule_resp.json()
    print(f"Schedule items tomorrow: {len(schedule)}")
    # Проверяем, что наше бронирование есть в расписании
    found = any(b["service_id"] == service_id for b in schedule)
    print(f"Booking found in schedule: {found}")
else:
    print(f"Schedule error: {schedule_resp.text[:200]}")

# Проверяем фильтрацию по другому тренеру (должен быть 0)
other_trainer = "11111111-1111-1111-1111-111111111111"
schedule_other = requests.get(
    f"{BASE}/services/trainer-schedule",
    headers=headers,
    params={
        "trainer_id": other_trainer,
        "date": tomorrow
    }
)
if schedule_other.status_code == 200:
    print(f"Schedule other trainer: {len(schedule_other.json())}")
else:
    print(f"Schedule other trainer error: {schedule_other.status_code}")
