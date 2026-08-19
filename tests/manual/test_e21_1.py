import requests
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
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

# Получаем клиента из БД
with engine.connect() as conn:
    result = conn.execute(text("SELECT id::text FROM clients LIMIT 1"))
    row = result.fetchone()
    if row:
        client_id = str(row[0])
        print(f"Client ID: {client_id}")
    else:
        print("❌ Нет клиентов")
        exit(1)

# Начисляем XP за посещение
xp_data = {
    "client_id": client_id,
    "amount": 10,
    "reason": "Посещение клуба"
}
xp_resp = requests.post(f"{BASE}/gamification/award-xp", headers=headers, json=xp_data)
print(f"XP Award Status: {xp_resp.status_code}")
print(f"XP Award Response: {xp_resp.text[:300]}")

# Проверяем уровень клиента
level_resp = requests.get(f"{BASE}/gamification/level", headers=headers, params={"client_id": client_id})
print(f"Level Status: {level_resp.status_code}")
print(f"Level Response: {level_resp.text[:300]}")
