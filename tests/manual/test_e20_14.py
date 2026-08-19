# tests/manual/test_e20_14.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Клиент генерирует QR
gen = requests.post("http://localhost:8001/api/v1/dynamic-qr/generate",
                    headers=headers,
                    json={"client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3"})
qr_payload = gen.json()["qr_payload"]
print(f"QR сгенерирован: {gen.status_code}")

# Сканер турникета отправляет QR
resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/turnstile",
                     headers=headers,
                     json={"qr_payload": qr_payload, "device_id": "turnstile_001"})
print(f"E20.14 Status: {resp.status_code}")
print(f"E20.14 Response: {resp.text[:500]}")
