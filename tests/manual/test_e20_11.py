# tests/manual/test_e20_11.py
import requests
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем текущий QR
qr1 = requests.get("http://localhost:8001/api/v1/dynamic-qr/my", headers=headers).json()
print(f"QR #1 id: {qr1['id']}, expires: {qr1['expires_at']}")

# Искусственно 'просрочиваем' его в БД (эмуляция того, что время вышло)
with engine.begin() as conn:
    conn.execute(text(
        "UPDATE dynamic_qr_codes SET expires_at = NOW() - INTERVAL '1 minute' WHERE id = :id"
    ), {"id": qr1["id"]})
print("QR #1 просрочен (эмуляция истечения)")

# Запрашиваем QR снова — должен быть создан НОВЫЙ
qr2 = requests.get("http://localhost:8001/api/v1/dynamic-qr/my", headers=headers).json()
print(f"QR #2 id: {qr2['id']}, expires: {qr2['expires_at']}")

if qr2["id"] != qr1["id"] and qr2["qr_payload"] != qr1["qr_payload"]:
    print("E20.11 PASS: QR автоматически обновлён, старый отозван (истёк)")
else:
    print("E20.11 FAIL: QR не обновлён!")

# Контроль: старый QR не должен проходить проверку
resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                     headers=headers, json={"qr_payload": qr1["qr_payload"]})
print(f"Old QR verify Status: {resp.status_code} (ожидаем 410)")
