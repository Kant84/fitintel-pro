# tests/manual/test_e20_6.py
import requests
import json
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Генерируем настоящий QR
gen = requests.post("http://localhost:8001/api/v1/dynamic-qr/generate",
                    headers=headers, json={"client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3"})
qr_payload = gen.json()["qr_payload"]

# Подделываем: меняем подпись на мусор
data = json.loads(base64.b64decode(qr_payload))
data["signature"] = "0" * 64  # фейковая подпись
fake_payload = base64.b64encode(json.dumps(data).encode()).decode()

# Проверяем поддельный QR
resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                     headers=headers, json={"qr_payload": fake_payload})
print(f"E20.6 Status: {resp.status_code}")
print(f"E20.6 Response: {resp.text[:500]}")
